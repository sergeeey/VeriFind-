-- Migration V002: Add data attribution columns for regulatory compliance
-- Week 11: SEC/FINRA compliance - track data source and freshness
-- Created: 2026-02-09

-- Add data_source column to verified_facts table
ALTER TABLE IF EXISTS verified_facts
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'yfinance';

-- Add data_freshness column to track when data was fetched
ALTER TABLE IF EXISTS verified_facts
ADD COLUMN IF NOT EXISTS data_freshness TIMESTAMPTZ DEFAULT NOW();

-- Add index for querying by data source
CREATE INDEX IF NOT EXISTS idx_verified_facts_data_source
ON verified_facts(data_source, created_at DESC);

-- Add index for data freshness queries (find stale data)
CREATE INDEX IF NOT EXISTS idx_verified_facts_freshness
ON verified_facts(data_freshness, data_source);

-- Add comment for documentation
COMMENT ON COLUMN verified_facts.data_source IS 
    'Source of market data: yfinance, alpha_vantage, polygon, cache';

COMMENT ON COLUMN verified_facts.data_freshness IS 
    'UTC timestamp when data was fetched from external API';

-- Create view for data freshness monitoring
CREATE OR REPLACE VIEW data_freshness_summary AS
SELECT 
    data_source,
    COUNT(*) as fact_count,
    MIN(data_freshness) as oldest_fetch,
    MAX(data_freshness) as newest_fetch,
    AVG(EXTRACT(EPOCH FROM (NOW() - data_freshness))) as avg_age_seconds
FROM verified_facts
GROUP BY data_source;

-- Grant permissions (adjust role name as needed)
-- GRANT SELECT ON data_freshness_summary TO ape_readonly;
