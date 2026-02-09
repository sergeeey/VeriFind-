"""Prometheus metrics for APE 2026 monitoring.

Week 11: Production metrics for data sources, failovers, and performance.

Metrics exposed:
- data_source_failover_total: Failover events between sources
- data_source_latency_seconds: API response times
- data_source_errors_total: Error counts by source and type
- cache_hit_total: Cache hits
- cache_miss_total: Cache misses
- data_freshness_seconds: Time since data was fetched
- api_quota_remaining: API quota tracking
"""

from prometheus_client import Counter, Histogram, Gauge, Info

# =============================================================================
# Data Source Metrics
# =============================================================================

# Failover counter: tracks automatic failovers between data sources
data_source_failover_total = Counter(
    'data_source_failover_total',
    'Number of failovers between data sources',
    ['from_source', 'to_source', 'ticker', 'reason']
)

# Latency histogram: tracks API response times
data_source_latency_seconds = Histogram(
    'data_source_latency_seconds',
    'Data source API response time in seconds',
    ['source', 'endpoint', 'ticker'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

# Error counter: tracks errors by source and type
data_source_errors_total = Counter(
    'data_source_errors_total',
    'Total errors from data sources',
    ['source', 'error_type', 'ticker']
)

# =============================================================================
# Cache Metrics
# =============================================================================

cache_hit_total = Counter(
    'cache_hit_total',
    'Cache hits by source',
    ['source', 'cache_type']
)

cache_miss_total = Counter(
    'cache_miss_total',
    'Cache misses by source',
    ['source', 'cache_type']
)

# =============================================================================
# Data Freshness Metrics
# =============================================================================

# Gauge: time since data was last updated (seconds)
data_freshness_seconds = Gauge(
    'data_freshness_seconds',
    'Time since data was last updated from external API',
    ['ticker', 'source']
)

# =============================================================================
# API Quota Metrics
# =============================================================================

# Gauge: remaining API quota (for services with daily limits)
api_quota_remaining = Gauge(
    'api_quota_remaining',
    'Remaining API quota for data source',
    ['source', 'quota_type']  # quota_type: 'daily', 'minute', etc.
)

# Info: API versions and config
api_info = Info(
    'ape_data_api',
    'Data source API information'
)

# =============================================================================
# Helper Functions
# =============================================================================

def record_data_source_latency(
    source: str,
    endpoint: str,
    ticker: str,
    latency_seconds: float
) -> None:
    """Record data source API latency.
    
    Args:
        source: Data source name (yfinance, alpha_vantage, etc.)
        endpoint: API endpoint/function
        ticker: Stock symbol
        latency_seconds: Response time
    """
    data_source_latency_seconds.labels(
        source=source,
        endpoint=endpoint,
        ticker=ticker
    ).observe(latency_seconds)


def record_data_source_error(
    source: str,
    error_type: str,
    ticker: str
) -> None:
    """Record data source error.
    
    Args:
        source: Data source name
        error_type: Type of error (timeout, rate_limit, network, etc.)
        ticker: Stock symbol
    """
    data_source_errors_total.labels(
        source=source,
        error_type=error_type,
        ticker=ticker
    ).inc()


def record_failover(
    from_source: str,
    to_source: str,
    ticker: str,
    reason: str
) -> None:
    """Record failover event.
    
    Args:
        from_source: Source that failed
        to_source: Source switched to
        ticker: Stock symbol
        reason: Reason for failover (timeout, empty, rate_limit, etc.)
    """
    data_source_failover_total.labels(
        from_source=from_source,
        to_source=to_source,
        ticker=ticker,
        reason=reason
    ).inc()


def record_cache_hit(source: str, cache_type: str = "memory") -> None:
    """Record cache hit.
    
    Args:
        source: Original data source
        cache_type: Type of cache (memory, redis, etc.)
    """
    cache_hit_total.labels(source=source, cache_type=cache_type).inc()


def record_cache_miss(source: str, cache_type: str = "memory") -> None:
    """Record cache miss.
    
    Args:
        source: Data source
        cache_type: Type of cache
    """
    cache_miss_total.labels(source=source, cache_type=cache_type).inc()


def update_data_freshness(ticker: str, source: str, age_seconds: float) -> None:
    """Update data freshness gauge.
    
    Args:
        ticker: Stock symbol
        source: Data source
        age_seconds: Time since data was fetched
    """
    data_freshness_seconds.labels(ticker=ticker, source=source).set(age_seconds)


def update_api_quota(source: str, quota_type: str, remaining: int) -> None:
    """Update API quota gauge.
    
    Args:
        source: Data source
        quota_type: Type of quota (daily, minute)
        remaining: Remaining quota
    """
    api_quota_remaining.labels(source=source, quota_type=quota_type).set(remaining)


def set_api_info(version: str, config: dict) -> None:
    """Set API info metric.
    
    Args:
        version: API version
        config: Configuration dict
    """
    api_info.info({
        'version': version,
        **{k: str(v) for k, v in config.items()}
    })


# =============================================================================
# Query Execution Metrics (for future use)
# =============================================================================

query_execution_total = Counter(
    'ape_query_execution_total',
    'Total query executions',
    ['status', 'node']  # status: success, error, timeout
)

query_execution_duration = Histogram(
    'ape_query_execution_duration_seconds',
    'Query execution duration',
    ['node'],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)
)

verified_facts_total = Counter(
    'ape_verified_facts_total',
    'Total verified facts created',
    ['status']  # status: success, error
)

confidence_score_distribution = Histogram(
    'ape_confidence_score_distribution',
    'Distribution of confidence scores',
    buckets=(0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0)
)
