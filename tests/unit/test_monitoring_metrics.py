"""Unit tests for monitoring metrics.

Week 11: Tests for Prometheus metrics.
"""

import pytest
from prometheus_client import REGISTRY

# Import metrics after to get fresh registry
from src.monitoring.metrics import (
    data_source_failover_total,
    data_source_latency_seconds,
    data_source_errors_total,
    cache_hit_total,
    cache_miss_total,
    data_freshness_seconds,
    api_quota_remaining,
    record_data_source_latency,
    record_data_source_error,
    record_failover,
    record_cache_hit,
    record_cache_miss,
    update_data_freshness,
    update_api_quota,
)


class TestMetrics:
    """Test Prometheus metrics."""

    def test_failover_counter_increments(self):
        """Test failover counter increments correctly."""
        # Get initial value
        initial = data_source_failover_total.labels(
            from_source='yfinance',
            to_source='alpha_vantage',
            ticker='AAPL',
            reason='timeout'
        )._value.get()
        
        # Record failover
        record_failover('yfinance', 'alpha_vantage', 'AAPL', 'timeout')
        
        # Check incremented
        after = data_source_failover_total.labels(
            from_source='yfinance',
            to_source='alpha_vantage',
            ticker='AAPL',
            reason='timeout'
        )._value.get()
        
        assert after == initial + 1

    def test_latency_histogram_records(self):
        """Test latency histogram records values."""
        record_data_source_latency(
            source='alpha_vantage',
            endpoint='TIME_SERIES_DAILY',
            ticker='AAPL',
            latency_seconds=1.5
        )
        
        # Check histogram recorded value
        metric = REGISTRY.get_sample_value(
            'data_source_latency_seconds_sum',
            {'source': 'alpha_vantage', 'endpoint': 'TIME_SERIES_DAILY', 'ticker': 'AAPL'}
        )
        assert metric >= 1.5

    def test_error_counter(self):
        """Test error counter."""
        initial = data_source_errors_total.labels(
            source='yfinance',
            error_type='timeout',
            ticker='AAPL'
        )._value.get()
        
        record_data_source_error('yfinance', 'timeout', 'AAPL')
        
        after = data_source_errors_total.labels(
            source='yfinance',
            error_type='timeout',
            ticker='AAPL'
        )._value.get()
        
        assert after == initial + 1

    def test_cache_hit_counter(self):
        """Test cache hit counter."""
        initial = cache_hit_total.labels(
            source='alpha_vantage',
            cache_type='memory'
        )._value.get()
        
        record_cache_hit('alpha_vantage', 'memory')
        
        after = cache_hit_total.labels(
            source='alpha_vantage',
            cache_type='memory'
        )._value.get()
        
        assert after == initial + 1

    def test_cache_miss_counter(self):
        """Test cache miss counter."""
        initial = cache_miss_total.labels(
            source='yfinance',
            cache_type='redis'
        )._value.get()
        
        record_cache_miss('yfinance', 'redis')
        
        after = cache_miss_total.labels(
            source='yfinance',
            cache_type='redis'
        )._value.get()
        
        assert after == initial + 1

    def test_data_freshness_gauge(self):
        """Test data freshness gauge."""
        update_data_freshness('AAPL', 'yfinance', 300.0)
        
        value = REGISTRY.get_sample_value(
            'data_freshness_seconds',
            {'ticker': 'AAPL', 'source': 'yfinance'}
        )
        assert value == 300.0

    def test_api_quota_gauge(self):
        """Test API quota gauge."""
        update_api_quota('alpha_vantage', 'daily', 450)
        
        value = REGISTRY.get_sample_value(
            'api_quota_remaining',
            {'source': 'alpha_vantage', 'quota_type': 'daily'}
        )
        assert value == 450

    def test_different_tickers_independent(self):
        """Metrics for different tickers are independent."""
        record_failover('yfinance', 'alpha_vantage', 'AAPL', 'timeout')
        record_failover('yfinance', 'alpha_vantage', 'MSFT', 'timeout')
        
        aapl_count = data_source_failover_total.labels(
            from_source='yfinance',
            to_source='alpha_vantage',
            ticker='AAPL',
            reason='timeout'
        )._value.get()
        
        msft_count = data_source_failover_total.labels(
            from_source='yfinance',
            to_source='alpha_vantage',
            ticker='MSFT',
            reason='timeout'
        )._value.get()
        
        # Both should have incremented independently
        assert aapl_count >= 1
        assert msft_count >= 1

    def test_multiple_latency_observations(self):
        """Histogram aggregates multiple observations."""
        record_data_source_latency('yfinance', 'fetch', 'AAPL', 0.5)
        record_data_source_latency('yfinance', 'fetch', 'AAPL', 1.0)
        record_data_source_latency('yfinance', 'fetch', 'AAPL', 1.5)
        
        count = REGISTRY.get_sample_value(
            'data_source_latency_seconds_count',
            {'source': 'yfinance', 'endpoint': 'fetch', 'ticker': 'AAPL'}
        )
        
        assert count >= 3
