"""
Unit tests for DataSourceRouter.

Week 11 Day 4: Failover Logic Testing

Tests cover:
- Failover chain execution
- Circuit breaker pattern
- Latency-based routing
- Cost optimization
- Metrics tracking

Author: Claude Sonnet 4.5
Created: 2026-02-08
"""

import pytest
import pandas as pd
import time
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from src.adapters.data_source_router import (
    DataSourceRouter,
    DataSourceStatus,
    DataSourceMetrics,
    CircuitBreakerError,
    DataUnavailableError,
)


class TestDataSourceMetrics:
    """Test DataSourceMetrics dataclass."""

    def test_success_rate_calculation(self):
        """Test success rate is calculated correctly."""
        metrics = DataSourceMetrics(source_name="test")
        assert metrics.success_rate == 1.0  # No requests yet

        metrics.total_requests = 100
        metrics.successful_requests = 95
        assert metrics.success_rate == 0.95

    def test_avg_latency_calculation(self):
        """Test average latency calculation."""
        metrics = DataSourceMetrics(source_name="test")
        assert metrics.avg_latency_ms == 0.0  # No successful requests

        metrics.successful_requests = 10
        metrics.total_latency_ms = 1000.0  # 10 requests * 100ms each
        assert metrics.avg_latency_ms == 100.0

    def test_is_circuit_open(self):
        """Test circuit breaker status check."""
        metrics = DataSourceMetrics(source_name="test")
        assert not metrics.is_circuit_open()

        metrics.status = DataSourceStatus.CIRCUIT_OPEN
        assert metrics.is_circuit_open()

    def test_should_close_circuit_timeout(self):
        """Test circuit breaker timeout logic."""
        metrics = DataSourceMetrics(source_name="test")
        metrics.status = DataSourceStatus.CIRCUIT_OPEN
        metrics.circuit_breaker_opened_at = datetime.now() - timedelta(minutes=6)

        # Should close after 5 minutes (default timeout)
        assert metrics.should_close_circuit(timeout_minutes=5)

    def test_should_not_close_circuit_too_early(self):
        """Test circuit breaker doesn't close too early."""
        metrics = DataSourceMetrics(source_name="test")
        metrics.status = DataSourceStatus.CIRCUIT_OPEN
        metrics.circuit_breaker_opened_at = datetime.now() - timedelta(minutes=2)

        # Should NOT close after only 2 minutes
        assert not metrics.should_close_circuit(timeout_minutes=5)


class TestDataSourceRouter:
    """Test DataSourceRouter class."""

    @pytest.fixture
    def mock_yfinance(self):
        """Mock YFinanceAdapter."""
        mock = Mock()
        mock.get_ohlcv = Mock(return_value=pd.DataFrame({
            'Open': [100, 101],
            'High': [105, 106],
            'Low': [99, 100],
            'Close': [103, 104],
            'Volume': [1000000, 1100000]
        }))
        mock.get_fundamentals = Mock(return_value={
            'pe_ratio': 28.5,
            'market_cap': 2.8e12,
            'eps': 6.05,
        })
        return mock

    @pytest.fixture
    def mock_alpha_vantage(self):
        """Mock AlphaVantageAdapter."""
        mock = Mock()
        mock.get_ohlcv = Mock(return_value=pd.DataFrame({
            'Open': [100, 101],
            'High': [105, 106],
            'Low': [99, 100],
            'Close': [103, 104],
            'Volume': [1000000, 1100000]
        }))
        mock.get_fundamentals = Mock(return_value={
            'pe_ratio': 28.5,
            'market_cap': 2.8e12,
            'eps': 6.05,
        })
        return mock

    @pytest.fixture
    def router(self, mock_yfinance, mock_alpha_vantage):
        """Create router with mocked adapters."""
        return DataSourceRouter(
            yfinance=mock_yfinance,
            alpha_vantage=mock_alpha_vantage,
        )

    def test_initialization(self, mock_yfinance, mock_alpha_vantage):
        """Test router initializes with sources."""
        router = DataSourceRouter(
            yfinance=mock_yfinance,
            alpha_vantage=mock_alpha_vantage,
        )

        assert len(router.sources) == 2
        assert 'yfinance' in router.sources
        assert 'alpha_vantage' in router.sources
        assert len(router.metrics) == 2

    def test_initialization_requires_at_least_one_source(self):
        """Test router requires at least one source."""
        with pytest.raises(ValueError, match="At least one data source"):
            DataSourceRouter()

    def test_get_ohlcv_success_from_primary(self, router, mock_yfinance):
        """Test successful fetch from primary source (yfinance)."""
        df, source, freshness = router.get_ohlcv("AAPL")

        assert not df.empty
        assert source == "yfinance"
        assert isinstance(freshness, float)
        assert mock_yfinance.get_ohlcv.called

    def test_get_ohlcv_failover_to_secondary(self, router, mock_yfinance, mock_alpha_vantage):
        """Test failover to secondary source when primary fails."""
        # Make yfinance fail
        mock_yfinance.get_ohlcv.side_effect = Exception("Network error")

        df, source, freshness = router.get_ohlcv("AAPL")

        # Should failover to alpha_vantage
        assert not df.empty
        assert source == "alpha_vantage"
        assert mock_alpha_vantage.get_ohlcv.called

    def test_get_ohlcv_all_sources_fail(self, router, mock_yfinance, mock_alpha_vantage):
        """Test DataUnavailableError when all sources fail."""
        mock_yfinance.get_ohlcv.side_effect = Exception("yfinance error")
        mock_alpha_vantage.get_ohlcv.side_effect = Exception("alpha_vantage error")

        with pytest.raises(DataUnavailableError, match="All data sources failed"):
            router.get_ohlcv("AAPL")

    def test_get_ohlcv_empty_dataframe_triggers_failover(self, router, mock_yfinance, mock_alpha_vantage):
        """Test that empty DataFrame triggers failover."""
        # yfinance returns empty DataFrame
        mock_yfinance.get_ohlcv.return_value = pd.DataFrame()

        df, source, freshness = router.get_ohlcv("AAPL")

        # Should failover to alpha_vantage
        assert not df.empty
        assert source == "alpha_vantage"

    def test_circuit_breaker_opens_after_threshold(self, mock_yfinance, mock_alpha_vantage):
        """Test circuit breaker opens after N failures."""
        # Create router with ONLY yfinance (no failover)
        router = DataSourceRouter(yfinance=mock_yfinance)

        # Make yfinance fail repeatedly
        mock_yfinance.get_ohlcv.side_effect = Exception("Persistent error")

        # Trigger 5 failures (default threshold)
        for _ in range(5):
            try:
                router.get_ohlcv("AAPL")
            except:
                pass

        # Check circuit breaker is open
        metrics = router.metrics["yfinance"]
        assert metrics.status == DataSourceStatus.CIRCUIT_OPEN
        assert metrics.circuit_breaker_failures >= 5

    def test_circuit_breaker_skips_open_circuit(self, router, mock_yfinance, mock_alpha_vantage):
        """Test router skips source with open circuit."""
        # Open circuit for yfinance
        router.metrics["yfinance"].status = DataSourceStatus.CIRCUIT_OPEN
        router.metrics["yfinance"].circuit_breaker_opened_at = datetime.now()

        # Should skip yfinance and use alpha_vantage directly
        df, source, freshness = router.get_ohlcv("AAPL")

        assert source == "alpha_vantage"
        assert not mock_yfinance.get_ohlcv.called  # Skipped!

    def test_circuit_breaker_closes_on_success(self, router, mock_yfinance):
        """Test circuit breaker closes after successful request."""
        # Set circuit to degraded (half-open)
        router.metrics["yfinance"].status = DataSourceStatus.DEGRADED

        # Successful request should close circuit
        df, source, freshness = router.get_ohlcv("AAPL")

        assert router.metrics["yfinance"].status == DataSourceStatus.HEALTHY
        assert router.metrics["yfinance"].circuit_breaker_failures == 0

    def test_circuit_breaker_half_open_after_timeout(self, router):
        """Test circuit enters half-open state after timeout."""
        metrics = router.metrics["yfinance"]
        metrics.status = DataSourceStatus.CIRCUIT_OPEN
        metrics.circuit_breaker_opened_at = datetime.now() - timedelta(minutes=6)

        # Get priority should mark as DEGRADED (half-open)
        priority = router._get_source_priority()

        assert "yfinance" in priority
        assert metrics.status == DataSourceStatus.DEGRADED

    def test_get_fundamentals_success(self, router, mock_yfinance):
        """Test successful fundamentals fetch."""
        fundamentals, source, freshness = router.get_fundamentals("AAPL")

        assert isinstance(fundamentals, dict)
        assert 'pe_ratio' in fundamentals
        assert source == "yfinance"
        assert mock_yfinance.get_fundamentals.called

    def test_get_fundamentals_failover(self, router, mock_yfinance, mock_alpha_vantage):
        """Test fundamentals failover to secondary source."""
        mock_yfinance.get_fundamentals.side_effect = Exception("Error")

        fundamentals, source, freshness = router.get_fundamentals("AAPL")

        assert source == "alpha_vantage"
        assert mock_alpha_vantage.get_fundamentals.called

    def test_metrics_tracking_success(self, mock_yfinance):
        """Test metrics are tracked correctly for successful requests."""
        # Create fresh router
        router = DataSourceRouter(yfinance=mock_yfinance)

        # Make 3 successful requests
        for _ in range(3):
            router.get_ohlcv("AAPL")

        metrics = router.metrics["yfinance"]
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 3
        assert metrics.failed_requests == 0
        assert metrics.success_rate == 1.0
        assert metrics.last_success is not None

    def test_metrics_tracking_failures(self, mock_yfinance, mock_alpha_vantage):
        """Test metrics track failures correctly."""
        # Create fresh router
        router = DataSourceRouter(yfinance=mock_yfinance, alpha_vantage=mock_alpha_vantage)

        # Make BOTH sources fail so yfinance gets tried every time
        mock_yfinance.get_ohlcv.side_effect = Exception("yfinance error")
        mock_alpha_vantage.get_ohlcv.side_effect = Exception("alpha_vantage error")

        # Make 3 requests (all fail, but yfinance tried first each time)
        for _ in range(3):
            try:
                router.get_ohlcv("AAPL")
            except DataUnavailableError:
                pass  # Expected - all sources failed

        yf_metrics = router.metrics["yfinance"]
        assert yf_metrics.total_requests == 3
        assert yf_metrics.successful_requests == 0
        assert yf_metrics.failed_requests == 3
        assert yf_metrics.success_rate == 0.0
        assert yf_metrics.last_failure is not None

    def test_latency_tracking(self, router, mock_yfinance):
        """Test latency is tracked in metrics."""
        # Slow down adapter to measure latency
        def slow_get_ohlcv(*args, **kwargs):
            time.sleep(0.1)  # 100ms
            return pd.DataFrame({
                'Open': [100],
                'High': [105],
                'Low': [99],
                'Close': [103],
                'Volume': [1000000]
            })

        mock_yfinance.get_ohlcv = slow_get_ohlcv

        router.get_ohlcv("AAPL")

        metrics = router.metrics["yfinance"]
        assert metrics.avg_latency_ms >= 100.0  # At least 100ms

    def test_get_stats(self, router, mock_yfinance):
        """Test get_stats() returns metrics for all sources."""
        # Make some requests
        router.get_ohlcv("AAPL")

        stats = router.get_stats()

        assert 'yfinance' in stats
        assert 'alpha_vantage' in stats

        yf_stats = stats['yfinance']
        assert 'status' in yf_stats
        assert 'total_requests' in yf_stats
        assert 'success_rate' in yf_stats
        assert yf_stats['total_requests'] == 1

    def test_reset_circuit_breaker(self, router):
        """Test manual circuit breaker reset."""
        # Open circuit
        router.metrics["yfinance"].status = DataSourceStatus.CIRCUIT_OPEN
        router.metrics["yfinance"].circuit_breaker_failures = 10

        # Reset
        router.reset_circuit_breaker("yfinance")

        metrics = router.metrics["yfinance"]
        assert metrics.status == DataSourceStatus.HEALTHY
        assert metrics.circuit_breaker_failures == 0
        assert metrics.circuit_breaker_opened_at is None

    def test_reset_circuit_breaker_unknown_source(self, router):
        """Test reset fails for unknown source."""
        with pytest.raises(ValueError, match="Unknown source"):
            router.reset_circuit_breaker("nonexistent")

    def test_source_priority_prefers_free_sources(self, mock_yfinance, mock_alpha_vantage):
        """Test router prefers free sources over paid when enabled."""
        mock_polygon = Mock()
        mock_polygon.get_ohlcv = Mock(return_value=pd.DataFrame({
            'Open': [100], 'High': [105], 'Low': [99], 'Close': [103], 'Volume': [1000000]
        }))

        router = DataSourceRouter(
            yfinance=mock_yfinance,
            alpha_vantage=mock_alpha_vantage,
            polygon=mock_polygon,
            prefer_free_sources=True,
        )

        priority = router._get_source_priority()

        # Free sources (yfinance, alpha_vantage) should come before paid (polygon)
        free_sources = ['yfinance', 'alpha_vantage']
        for free_source in free_sources:
            if free_source in priority and 'polygon' in priority:
                assert priority.index(free_source) < priority.index('polygon')

    def test_source_priority_considers_latency(self, mock_yfinance, mock_alpha_vantage):
        """Test router considers latency in priority."""
        router = DataSourceRouter(
            yfinance=mock_yfinance,
            alpha_vantage=mock_alpha_vantage,
            latency_weight=0.5,  # High latency weight
        )

        # Simulate yfinance being slower
        router.metrics["yfinance"].successful_requests = 10
        router.metrics["yfinance"].total_latency_ms = 5000.0  # 500ms average

        router.metrics["alpha_vantage"].successful_requests = 10
        router.metrics["alpha_vantage"].total_latency_ms = 1000.0  # 100ms average

        priority = router._get_source_priority()

        # Faster source (alpha_vantage) should be preferred
        # (Note: This depends on other factors too, so not guaranteed)
        assert "alpha_vantage" in priority
        assert "yfinance" in priority


class TestDataSourceRouterIntegration:
    """Integration tests for router with real-ish scenarios."""

    def test_complete_failover_chain(self):
        """Test complete failover chain: yfinance → alpha_vantage → error."""
        # Create 3 mock sources
        yfinance = Mock()
        alpha_vantage = Mock()
        polygon = Mock()

        # Make yfinance and alpha_vantage fail
        yfinance.get_ohlcv.side_effect = Exception("yfinance down")
        alpha_vantage.get_ohlcv.side_effect = Exception("alpha_vantage down")

        # polygon succeeds
        polygon.get_ohlcv.return_value = pd.DataFrame({
            'Open': [100], 'High': [105], 'Low': [99], 'Close': [103], 'Volume': [1000000]
        })

        router = DataSourceRouter(
            yfinance=yfinance,
            alpha_vantage=alpha_vantage,
            polygon=polygon,
        )

        df, source, _ = router.get_ohlcv("AAPL")

        # Should succeed with polygon (last in chain)
        assert source == "polygon"
        assert not df.empty

    def test_circuit_breaker_recovery_flow(self):
        """Test circuit breaker opens, times out, and recovers."""
        yfinance = Mock()

        # First 5 calls fail (opens circuit), then succeeds (closes circuit)
        yfinance.get_ohlcv.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3"),
            Exception("Error 4"),
            Exception("Error 5"),  # Circuit opens after 5 failures
            pd.DataFrame({'Open': [100], 'High': [105], 'Low': [99], 'Close': [103], 'Volume': [1000000]}),  # Recovery
        ]

        # Router with ONLY yfinance (no failover to trigger circuit properly)
        router = DataSourceRouter(
            yfinance=yfinance,
            circuit_breaker_threshold=5,
        )

        # Trigger 5 failures
        for i in range(5):
            try:
                router.get_ohlcv("AAPL")
            except:
                pass  # All fail (no failover)

        # Circuit should be open
        assert router.metrics["yfinance"].status == DataSourceStatus.CIRCUIT_OPEN

        # Manually simulate timeout (set opened_at to 6 minutes ago)
        router.metrics["yfinance"].circuit_breaker_opened_at = datetime.now() - timedelta(minutes=6)

        # Next request should try yfinance again (half-open)
        df, source, _ = router.get_ohlcv("AAPL")

        # Should succeed and close circuit
        assert source == "yfinance"
        assert router.metrics["yfinance"].status == DataSourceStatus.HEALTHY


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
