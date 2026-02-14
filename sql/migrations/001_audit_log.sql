-- Week 13 Day 1: Compliance Audit Trail
-- Immutable audit log for financial analysis requests (regulatory requirement)

-- Run in TimescaleDB (ape-timescaledb container, port 5433)
-- psql -U postgres -d ape_db -f sql/migrations/001_audit_log.sql

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,  -- 'analysis_request', 'prediction', 'recommendation'
    query_id TEXT,
    endpoint TEXT,
    request_hash TEXT,  -- SHA-256 of request (not the request itself - PII protection)
    response_summary JSONB,  -- recommendation, confidence, cost (no PII)
    llm_providers JSONB,  -- which models were used
    disclaimer_version TEXT DEFAULT '2.0',
    client_ip_hash TEXT,  -- hashed IP for privacy
    processing_time_ms FLOAT,
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('audit_log', 'timestamp', if_not_exists => TRUE);

-- Create indexes for compliance queries
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log (event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_query_id ON audit_log (query_id);
CREATE INDEX IF NOT EXISTS idx_audit_endpoint ON audit_log (endpoint, timestamp DESC);

-- Retention policy: keep 2 years (regulatory requirement: SEC/MiFID II)
SELECT add_retention_policy('audit_log', INTERVAL '2 years', if_not_exists => TRUE);

-- Grant permissions
GRANT SELECT, INSERT ON audit_log TO ape;

-- Comment on table
COMMENT ON TABLE audit_log IS 'Immutable audit trail for financial analysis. Required for SEC/EU AI Act compliance. Retention: 2 years.';
COMMENT ON COLUMN audit_log.request_hash IS 'SHA-256 hash of request for deduplication (not full request - PII protection)';
COMMENT ON COLUMN audit_log.client_ip_hash IS 'Hashed client IP (privacy protection, 16-char truncated SHA-256)';
