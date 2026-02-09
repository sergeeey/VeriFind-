-- Migration: API Costs Tracking Table
-- Week 11 Day 4: Cost tracking middleware
-- Author: Claude Sonnet 4.5
-- Date: 2026-02-08

-- Create api_costs table to track LLM and data provider API calls
CREATE TABLE IF NOT EXISTS api_costs (
    id SERIAL PRIMARY KEY,

    -- Request identification
    request_id UUID NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    http_method VARCHAR(10) NOT NULL,

    -- Provider information
    provider VARCHAR(50) NOT NULL,  -- 'anthropic', 'openai', 'deepseek', 'yfinance', 'alpha_vantage'
    model VARCHAR(100),  -- e.g., 'claude-sonnet-4-5', 'gpt-4o', 'deepseek-chat' (NULL for data providers)

    -- Usage metrics
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,

    -- Cost calculation (in USD)
    cost_usd DECIMAL(10, 6) NOT NULL,  -- Total cost for this call

    -- Request metadata
    user_id VARCHAR(255),  -- Optional: track per-user costs
    ticker VARCHAR(20),  -- Stock ticker if applicable
    query_type VARCHAR(50),  -- 'analysis', 'forecast', 'qa', 'data_fetch'

    -- Performance metrics
    latency_ms INTEGER,  -- Response time
    status_code INTEGER,  -- HTTP status code
    error_message TEXT,  -- Error details if failed

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Indexes for efficient querying
    INDEX idx_request_id (request_id),
    INDEX idx_provider (provider),
    INDEX idx_created_at (created_at),
    INDEX idx_ticker (ticker),
    INDEX idx_user_id (user_id)
);

-- Create view for daily cost summary
CREATE OR REPLACE VIEW daily_cost_summary AS
SELECT
    DATE(created_at) as date,
    provider,
    model,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cache_read_tokens) as total_cache_read_tokens,
    SUM(cache_write_tokens) as total_cache_write_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(latency_ms) as avg_latency_ms
FROM api_costs
GROUP BY DATE(created_at), provider, model
ORDER BY date DESC, total_cost_usd DESC;

-- Create view for provider cost breakdown
CREATE OR REPLACE VIEW provider_cost_breakdown AS
SELECT
    provider,
    model,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(cost_usd) as avg_cost_per_request,
    AVG(latency_ms) as avg_latency_ms
FROM api_costs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY provider, model
ORDER BY total_cost_usd DESC;

-- Comment on table
COMMENT ON TABLE api_costs IS 'Tracks all API calls (LLM and data providers) with cost and usage metrics';

-- Comment on columns
COMMENT ON COLUMN api_costs.request_id IS 'Unique identifier for each request (same as FastAPI request_id)';
COMMENT ON COLUMN api_costs.provider IS 'API provider: anthropic, openai, deepseek, yfinance, alpha_vantage';
COMMENT ON COLUMN api_costs.cost_usd IS 'Total cost in USD (calculated using provider pricing)';
COMMENT ON COLUMN api_costs.cache_read_tokens IS 'Prompt cache hits (Anthropic only)';
COMMENT ON COLUMN api_costs.cache_write_tokens IS 'Prompt cache writes (Anthropic only)';
