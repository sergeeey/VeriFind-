"""
Prometheus metrics for APE API.

Week 9 Day 2: Monitoring & Observability
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Callable
import time
from functools import wraps


# ============================================================================
# HTTP Metrics
# ============================================================================

# Request counter by method, endpoint, and status
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Request duration histogram
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Request size histogram
http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=(100, 1000, 10000, 100000, 1000000)
)

# Response size histogram
http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=(100, 1000, 10000, 100000, 1000000)
)

# Active requests gauge
http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint']
)


# ============================================================================
# Business Metrics
# ============================================================================

# Query metrics
queries_submitted_total = Counter(
    'queries_submitted_total',
    'Total number of queries submitted',
    ['priority']
)

queries_completed_total = Counter(
    'queries_completed_total',
    'Total number of queries completed',
    ['status']  # completed, failed
)

query_execution_duration_seconds = Histogram(
    'query_execution_duration_seconds',
    'Query execution time in seconds',
    ['status'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

# Pipeline metrics
pipeline_node_duration_seconds = Histogram(
    'pipeline_node_duration_seconds',
    'Pipeline node execution time',
    ['node'],  # PLAN, FETCH, VEE, GATE, DEBATE
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120)
)

pipeline_node_executions_total = Counter(
    'pipeline_node_executions_total',
    'Total pipeline node executions',
    ['node', 'status']  # success, failed
)

# Fact generation metrics
verified_facts_generated_total = Counter(
    'verified_facts_generated_total',
    'Total verified facts generated'
)

facts_confidence_score = Histogram(
    'facts_confidence_score',
    'Confidence scores of generated facts',
    buckets=(0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0)
)

# WebSocket metrics
websocket_connections_total = Gauge(
    'websocket_connections_total',
    'Number of active WebSocket connections'
)

websocket_messages_sent_total = Counter(
    'websocket_messages_sent_total',
    'Total WebSocket messages sent',
    ['message_type']  # subscribe, unsubscribe, update
)

websocket_messages_received_total = Counter(
    'websocket_messages_received_total',
    'Total WebSocket messages received',
    ['action']  # subscribe, unsubscribe, ping, auth
)


# ============================================================================
# Error Metrics
# ============================================================================

exceptions_total = Counter(
    'exceptions_total',
    'Total exceptions raised',
    ['exception_type', 'severity']
)

validation_errors_total = Counter(
    'validation_errors_total',
    'Total validation errors',
    ['error_type']  # sql_injection, xss, command_injection, etc.
)

rate_limit_violations_total = Counter(
    'rate_limit_violations_total',
    'Total rate limit violations',
    ['api_key']
)


# ============================================================================
# External Service Metrics
# ============================================================================

external_api_requests_total = Counter(
    'external_api_requests_total',
    'Total external API requests',
    ['service', 'status']  # anthropic, openai, alpha_vantage
)

external_api_duration_seconds = Histogram(
    'external_api_duration_seconds',
    'External API request duration',
    ['service'],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30)
)


# ============================================================================
# Database Metrics
# ============================================================================

database_queries_total = Counter(
    'database_queries_total',
    'Total database queries',
    ['database', 'operation']  # timescaledb/neo4j, select/insert/update
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration',
    ['database', 'operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

database_connection_pool_size = Gauge(
    'database_connection_pool_size',
    'Number of connections in pool',
    ['database', 'state']  # idle, active
)


# ============================================================================
# Cache Metrics
# ============================================================================

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # get/set, hit/miss
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio (0-1)'
)


# ============================================================================
# System Metrics
# ============================================================================

# Application info
app_info = Info(
    'app_info',
    'Application information'
)

# Set app info (call once at startup)
def set_app_info(version: str, environment: str):
    """Set application information."""
    app_info.info({
        'version': version,
        'environment': environment,
        'name': 'APE-2026-API'
    })


# ============================================================================
# Metric Decorators
# ============================================================================

def track_query_execution(status: str = "completed"):
    """
    Decorator to track query execution metrics.

    Usage:
        @track_query_execution(status="completed")
        def execute_query():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                queries_completed_total.labels(status=status).inc()
                return result
            except Exception as e:
                queries_completed_total.labels(status="failed").inc()
                raise
            finally:
                duration = time.time() - start_time
                query_execution_duration_seconds.labels(status=status).observe(duration)

        return wrapper
    return decorator


def track_pipeline_node(node: str):
    """
    Decorator to track pipeline node execution.

    Usage:
        @track_pipeline_node(node="PLAN")
        def plan_node():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                pipeline_node_executions_total.labels(node=node, status="success").inc()
                return result
            except Exception as e:
                pipeline_node_executions_total.labels(node=node, status="failed").inc()
                raise
            finally:
                duration = time.time() - start_time
                pipeline_node_duration_seconds.labels(node=node).observe(duration)

        return wrapper
    return decorator


def track_external_api_call(service: str):
    """
    Decorator to track external API calls.

    Usage:
        @track_external_api_call(service="anthropic")
        async def call_claude():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                external_api_requests_total.labels(service=service, status="success").inc()
                return result
            except Exception as e:
                external_api_requests_total.labels(service=service, status="failed").inc()
                raise
            finally:
                duration = time.time() - start_time
                external_api_duration_seconds.labels(service=service).observe(duration)

        return wrapper
    return decorator


# ============================================================================
# Helper Functions
# ============================================================================

def record_validation_error(error_type: str):
    """Record a validation error."""
    validation_errors_total.labels(error_type=error_type).inc()


def record_rate_limit_violation(api_key: str):
    """Record a rate limit violation."""
    rate_limit_violations_total.labels(api_key=api_key).inc()


def record_exception(exception_type: str, severity: str):
    """Record an exception."""
    exceptions_total.labels(exception_type=exception_type, severity=severity).inc()


def record_verified_fact(confidence_score: float):
    """Record a verified fact generation."""
    verified_facts_generated_total.inc()
    facts_confidence_score.observe(confidence_score)


def update_cache_hit_ratio(hits: int, total: int):
    """Update cache hit ratio metric."""
    if total > 0:
        ratio = hits / total
        cache_hit_ratio.set(ratio)
