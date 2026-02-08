"""Unit tests for DataSourceRouter.

Week 11: Tests for failover logic and multi-source routing.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime

from src.adapters.data_source_router import (
    DataSourceRouter,
    DataSourceResult,
    DataSourcePriority
)


class TestDataSourceRouter:
    """Test DataSourceRouter functionality."""

    @pytest.fixture
    def router_no_av(self):
        """Router without AlphaVantage."""
        return DataSourceRouter(
            alpha_vantage_key=None,
            enable_metrics=False
        )

    @pytest.fixture
    def router_with_av(self):
        """Router with AlphaVantage mock."""
        with patch('src.adapters.data_source_router.AlphaVantageAdapter') as mock_av:
            mock_instance = Mock()
            mock_instance.get_circuit_state.return_value = "closed"
            mock_av.return_value = mock_instance
            
            router = DataSourceRouter(
                alpha_vantage_key="test_key",
                enable_metrics=False
            )
            return router

    def test_initialization_no_alpha_vantage(self, router_no_av):
        """Router works without AlphaVantage."""
        assert router_no_av._alpha_vantage is None
        health = router_no_av.get_health()
        assert health['alpha_vantage']['status'] == 'not_configured'

    def test_initialization_with_alpha_vantage(self, router_with_av):
        """Router initializes AlphaVantage when key provided."""
        assert router_with_av._alpha_vantage is not None

    def test_yfinance_success(self, router_no_av):
        """Primary source (yfinance) returns data."""
        with patch.object(router_no_av._yfinance, 'fetch_ohlcv') as mock_fetch:
            mock_df = pd.DataFrame({
                'Open': [100.0],
                'High': [105.0],
                'Low': [99.0],
                'Close': [103.0],
                'Volume': [1000000]
            })
            mock_fetch.return_value = mock_df
            
            result = router_no_av.get_ohlcv("AAPL")
            
            assert result.source == "yfinance"
            assert not result.is_cached
            assert not result.data.empty
            assert result.error is None

    def test_failover_to_alpha_vantage(self, router_with_av):
        """Failover to AlphaVantage when yfinance fails."""
        # yfinance fails
        router_with_av._yfinance.fetch_ohlcv = Mock(return_value=pd.DataFrame())
        
        # AlphaVantage succeeds
        mock_df = pd.DataFrame({'Close': [100.0]})
        router_with_av._alpha_vantage.get_ohlcv.return_value = mock_df
        
        result = router_with_av.get_ohlcv("AAPL")
        
        assert result.source == "alpha_vantage"
        assert not result.data.empty

    def test_failover_to_cache(self, router_no_av):
        """Failover to cache when all sources fail."""
        # All sources fail
        router_no_av._yfinance.fetch_ohlcv = Mock(return_value=pd.DataFrame())
        
        # But we have cached data
        cached_df = pd.DataFrame({'Close': [100.0]})
        router_no_av.cache_result("AAPL", None, None, "1d", cached_df)
        
        result = router_no_av.get_ohlcv("AAPL")
        
        assert result.source == "cache"
        assert result.is_cached
        assert "stale data" in result.error.lower()

    def test_all_sources_fail(self, router_no_av):
        """Return empty when all sources fail."""
        router_no_av._yfinance.fetch_ohlcv = Mock(return_value=pd.DataFrame())
        
        result = router_no_av.get_ohlcv("INVALID_TICKER")
        
        assert result.source == "error"
        assert result.data.empty
        assert "All data sources failed" in result.error

    def test_date_filtering_passed_to_yfinance(self, router_no_av):
        """Date parameters passed to underlying adapter."""
        with patch.object(router_no_av._yfinance, 'fetch_ohlcv') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            router_no_av.get_ohlcv(
                "AAPL",
                start_date="2024-01-01",
                end_date="2024-12-31"
            )
            
            mock_fetch.assert_called_once_with(
                "AAPL",
                "2024-01-01",
                "2024-12-31",
                "1d"
            )

    def test_fundamentals_primary_source(self, router_no_av):
        """Fundamentals from primary source."""
        with patch.object(router_no_av._yfinance, 'fetch_fundamentals') as mock_fetch:
            mock_fetch.return_value = {'pe_ratio': 25.0, 'market_cap': 1e12}
            
            result = router_no_av.get_fundamentals("AAPL")
            
            assert result.source == "yfinance"
            assert result.data['pe_ratio'] == 25.0

    def test_fundamentals_empty_fallback(self, router_no_av):
        """Fundamentals failover when primary returns empty."""
        router_no_av._yfinance.fetch_fundamentals = Mock(return_value={})
        
        result = router_no_av.get_fundamentals("AAPL")
        
        assert result.source == "error"
        assert "Could not fetch fundamentals" in result.error

    def test_health_status(self, router_with_av):
        """Health status reflects adapter states."""
        health = router_with_av.get_health()
        
        assert 'yfinance' in health
        assert 'alpha_vantage' in health
        assert 'cache' in health
        
        assert health['yfinance']['status'] == 'healthy'

    def test_last_successful_source_tracking(self, router_no_av):
        """Track last successful source per ticker."""
        with patch.object(router_no_av._yfinance, 'fetch_ohlcv') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame({'Close': [100.0]})
            
            # Initially None
            assert router_no_av.get_last_successful_source("AAPL") is None
            
            # After successful fetch
            router_no_av.get_ohlcv("AAPL")
            assert router_no_av.get_last_successful_source("AAPL") == "yfinance"

    def test_clear_cache(self, router_no_av):
        """Clear cache removes all entries."""
        df = pd.DataFrame({'Close': [100.0]})
        router_no_av.cache_result("AAPL", None, None, "1d", df)
        
        assert len(router_no_av._cache) > 0
        
        router_no_av.clear_cache()
        assert len(router_no_av._cache) == 0


class TestDataSourceResult:
    """Test DataSourceResult dataclass."""

    def test_result_creation(self):
        """Create result with all fields."""
        df = pd.DataFrame({'Close': [100.0]})
        result = DataSourceResult(
            data=df,
            source="yfinance",
            is_cached=False,
            fetched_at=datetime.utcnow(),
            error=None
        )
        
        assert result.source == "yfinance"
        assert not result.is_cached
        assert result.error is None

    def test_cached_result(self):
        """Create cached result with error message."""
        result = DataSourceResult(
            data=pd.DataFrame(),
            source="cache",
            is_cached=True,
            fetched_at=datetime.utcnow(),
            error="Serving stale data"
        )
        
        assert result.is_cached
        assert "stale" in result.error


class TestDataSourcePriority:
    """Test priority enum."""

    def test_priority_order(self):
        """Priority order is correct."""
        assert DataSourcePriority.YFINANCE.value == 1
        assert DataSourcePriority.ALPHA_VANTAGE.value == 2
        assert DataSourcePriority.CACHE.value == 3
