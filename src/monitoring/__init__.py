"""Monitoring module for APE 2026.

Week 11: Prometheus metrics and observability.
"""

from .metrics import (
    data_source_failover_total,
    data_source_latency_seconds,
    data_source_errors_total,
    cache_hit_total,
    cache_miss_total,
    data_freshness_seconds,
    api_quota_remaining,
    query_execution_total,
    query_execution_duration,
    verified_facts_total,
    confidence_score_distribution,
    record_data_source_latency,
    record_data_source_error,
    record_failover,
    record_cache_hit,
    record_cache_miss,
    update_data_freshness,
    update_api_quota,
)

__all__ = [
    'data_source_failover_total',
    'data_source_latency_seconds',
    'data_source_errors_total',
    'cache_hit_total',
    'cache_miss_total',
    'data_freshness_seconds',
    'api_quota_remaining',
    'query_execution_total',
    'query_execution_duration',
    'verified_facts_total',
    'confidence_score_distribution',
    'record_data_source_latency',
    'record_data_source_error',
    'record_failover',
    'record_cache_hit',
    'record_cache_miss',
    'update_data_freshness',
    'update_api_quota',
]
