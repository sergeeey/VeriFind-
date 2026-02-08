-- APE 2026 - TimescaleDB Initial Setup
-- Week 1 Day 1: Database schema creation
-- Creates hypertables, indexes, compression policies, continuous aggregates

-- ============================================================================
-- 1. Enable TimescaleDB Extension
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 2. Market Data Hypertable (OHLCV + Volume)
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMPTZ NOT NULL,
    ticker TEXT NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    source TEXT,  -- 'yfinance', 'FRED', 'alpha_vantage', etc.

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable (partitioned by time)
SELECT create_hypertable(
    'market_data',
    'time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 days'  -- One chunk per week
);

-- ============================================================================
-- 3. Indexes for Common Query Patterns
-- ============================================================================

-- Primary query pattern: ticker + time range
CREATE INDEX IF NOT EXISTS idx_market_data_ticker_time
ON market_data (ticker, time DESC);

-- Source filtering (for data quality checks)
CREATE INDEX IF NOT EXISTS idx_market_data_source
ON market_data (source, time DESC);

-- Composite index for aggregations
CREATE INDEX IF NOT EXISTS idx_market_data_ticker_source_time
ON market_data (ticker, source, time DESC);

-- ============================================================================
-- 4. Compression Policy (After 7 Days)
-- ============================================================================

-- Enable compression on the hypertable
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ticker',  -- Segment by ticker for better compression
    timescaledb.compress_orderby = 'time DESC'   -- Order within segments
);

-- Automatic compression policy: compress chunks older than 7 days
SELECT add_compression_policy(
    'market_data',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- 5. Continuous Aggregate: Daily Summary
-- ============================================================================

-- Materialized view for daily OHLCV aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    ticker,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS total_volume,
    COUNT(*) AS data_points,
    MAX(source) AS primary_source  -- Most common source (approximation)
FROM market_data
GROUP BY day, ticker
WITH NO DATA;  -- Don't populate yet (will be done incrementally)

-- Refresh policy: update every hour
SELECT add_continuous_aggregate_policy(
    'daily_summary',
    start_offset => INTERVAL '3 days',  -- Start refreshing 3 days back
    end_offset => INTERVAL '1 hour',    -- Up to 1 hour ago
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Index on the continuous aggregate
CREATE INDEX IF NOT EXISTS idx_daily_summary_ticker_day
ON daily_summary (ticker, day DESC);

-- ============================================================================
-- 6. Retention Policy (Optional - for MVP, keep all data)
-- ============================================================================

-- Uncomment to enable automatic data deletion after 5 years
-- SELECT add_retention_policy(
--     'market_data',
--     INTERVAL '5 years',
--     if_not_exists => TRUE
-- );

-- ============================================================================
-- 7. Execution Logs Table (VEE Sandbox Logs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL,
    step_id TEXT NOT NULL,

    -- Execution details
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms INTEGER,
    status TEXT NOT NULL,  -- 'success', 'error', 'timeout'

    -- Code and output
    code_hash TEXT,  -- SHA256 of executed code
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,

    -- Resources
    memory_used_mb INTEGER,
    cpu_time_ms INTEGER,

    -- Metadata
    sandbox_image TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable for execution logs
SELECT create_hypertable(
    'execution_logs',
    'executed_at',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Indexes for execution logs
CREATE INDEX IF NOT EXISTS idx_execution_logs_episode
ON execution_logs (episode_id, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_execution_logs_status
ON execution_logs (status, executed_at DESC);

-- Compression policy for logs (after 30 days)
ALTER TABLE execution_logs SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'episode_id, status',
    timescaledb.compress_orderby = 'executed_at DESC'
);

SELECT add_compression_policy(
    'execution_logs',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- 8. Helper Functions
-- ============================================================================

-- Function to calculate simple returns
CREATE OR REPLACE FUNCTION calculate_returns(
    ticker_symbol TEXT,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ
)
RETURNS TABLE(time TIMESTAMPTZ, return_pct NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.time,
        (t.close - LAG(t.close) OVER (ORDER BY t.time)) / LAG(t.close) OVER (ORDER BY t.time) * 100 AS return_pct
    FROM market_data t
    WHERE
        t.ticker = ticker_symbol
        AND t.time BETWEEN start_date AND end_date
    ORDER BY t.time;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate volatility (standard deviation of returns)
CREATE OR REPLACE FUNCTION calculate_volatility(
    ticker_symbol TEXT,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ
)
RETURNS NUMERIC AS $$
DECLARE
    vol NUMERIC;
BEGIN
    SELECT STDDEV(return_pct) INTO vol
    FROM calculate_returns(ticker_symbol, start_date, end_date);

    RETURN COALESCE(vol, 0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. Sample Data (For Testing)
-- ============================================================================

-- Insert sample SPY data for testing
INSERT INTO market_data (time, ticker, open, high, low, close, volume, source)
VALUES
    ('2024-01-15 09:30:00-05', 'SPY', 480.50, 482.30, 479.80, 481.75, 50000000, 'test_data'),
    ('2024-01-16 09:30:00-05', 'SPY', 481.80, 483.20, 480.50, 482.90, 52000000, 'test_data'),
    ('2024-01-17 09:30:00-05', 'SPY', 482.90, 485.00, 482.00, 484.25, 48000000, 'test_data')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. Verification Queries
-- ============================================================================

-- Check hypertable configuration
SELECT * FROM timescaledb_information.hypertables
WHERE hypertable_name IN ('market_data', 'execution_logs');

-- Check compression policies
SELECT * FROM timescaledb_information.compression_settings
WHERE hypertable_name IN ('market_data', 'execution_logs');

-- Check continuous aggregates
SELECT * FROM timescaledb_information.continuous_aggregates
WHERE view_name = 'daily_summary';

-- Test query performance (should be <100ms)
EXPLAIN ANALYZE
SELECT * FROM market_data
WHERE ticker = 'SPY'
  AND time BETWEEN '2024-01-01' AND '2024-01-31'
ORDER BY time DESC;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ TimescaleDB setup complete!';
    RAISE NOTICE '✅ Hypertables: market_data, execution_logs';
    RAISE NOTICE '✅ Continuous aggregate: daily_summary';
    RAISE NOTICE '✅ Compression policies: enabled';
    RAISE NOTICE '✅ Sample data: 3 SPY records inserted';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Test query latency: SELECT * FROM market_data WHERE ticker = ''SPY'' LIMIT 10;';
    RAISE NOTICE '2. Ingest historical data: python scripts/ingest_historical_data.py';
    RAISE NOTICE '3. Verify compression: SELECT * FROM timescaledb_information.compressed_chunk_stats;';
END $$;
