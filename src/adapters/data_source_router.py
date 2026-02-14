"""Data Source Router with automatic failover.

Week 11: Production-grade failover between yfinance, AlphaVantage, and cache.

Failover chain:
1. yfinance (primary, free, real-time)
2. alpha_vantage (secondary, free tier 5calls/min)
3. cache (tertiary, stale data acceptable)
4. error (fail gracefully)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import pandas as pd

# Import adapters at module level for testability
from .yfinance_adapter import YFinanceAdapter
from .alpha_vantage_adapter import AlphaVantageAdapter
from .fred_adapter import FredAdapter

logger = logging.getLogger(__name__)


class DataSourcePriority(Enum):
    """Priority order for data sources."""
    YFINANCE = 1
    ALPHA_VANTAGE = 2
    CACHE = 3


@dataclass
class DataSourceResult:
    """Result from data source with metadata."""
    data: Any  # DataFrame or Dict
    source: str  # 'yfinance', 'alpha_vantage', 'cache'
    is_cached: bool
    fetched_at: datetime
    error: Optional[str] = None


class DataSourceRouter:
    """Routes data requests across multiple sources with failover.
    
    Features:
    - Automatic failover on primary source failure
    - Prometheus metrics for monitoring
    - Cache-as-fallback for degraded mode
    - Data freshness tracking
    
    Usage:
        router = DataSourceRouter(
            alpha_vantage_key="YOUR_KEY"
        )
        result = router.get_ohlcv("AAPL", "2024-01-01", "2024-12-31")
        print(f"Data from: {result.source}")  # 'yfinance' or 'alpha_vantage'
    """

    def __init__(
        self,
        alpha_vantage_key: Optional[str] = None,
        fred_api_key: Optional[str] = None,
        enable_metrics: bool = True,
        cache_ttl_seconds: int = 3600
    ):
        """Initialize router with data sources.

        Args:
            alpha_vantage_key: API key for AlphaVantage (optional)
            fred_api_key: API key for FRED (optional, week 14 integration)
            enable_metrics: Enable Prometheus metrics
            cache_ttl_seconds: Cache time-to-live
        """
        # Initialize primary source (always available)
        self._yfinance = YFinanceAdapter(cache_ttl_seconds=cache_ttl_seconds)

        # Initialize secondary source (if key provided)
        self._alpha_vantage: Optional[Any] = None
        if alpha_vantage_key:
            try:
                self._alpha_vantage = AlphaVantageAdapter(
                    api_key=alpha_vantage_key,
                    enable_metrics=enable_metrics
                )
                logger.info("AlphaVantage adapter initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AlphaVantage: {e}")

        # Initialize FRED adapter (Week 14: Macro economic data)
        self._fred: Optional[Any] = None
        try:
            self._fred = FredAdapter(
                api_key=fred_api_key,
                cache_ttl_seconds=86400,  # 24h TTL for economic data
                enable_metrics=enable_metrics
            )
            logger.info("FRED adapter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize FRED: {e}")
        
        # Initialize cache (in-memory)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = cache_ttl_seconds
        
        # Metrics
        self._enable_metrics = enable_metrics
        if enable_metrics:
            try:
                from src.monitoring.metrics import data_source_failover_total
                self._failover_metric = data_source_failover_total
            except ImportError:
                logger.warning("Metrics not available")
                self._failover_metric = None
        else:
            self._failover_metric = None
        
        # Track last successful source per ticker
        self._last_successful_source: Dict[str, str] = {}

    def get_ohlcv(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> DataSourceResult:
        """Fetch OHLCV data with automatic failover.
        
        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1d only for now)
            
        Returns:
            DataSourceResult with data and metadata
        """
        fetched_at = datetime.utcnow()
        
        # Try 1: yfinance (primary)
        try:
            logger.info(f"Fetching {ticker} from yfinance...")
            df = self._yfinance.fetch_ohlcv(ticker, start_date, end_date, interval)
            
            if not df.empty:
                self._last_successful_source[ticker] = "yfinance"
                logger.info(f"✓ yfinance success for {ticker}")
                return DataSourceResult(
                    data=df,
                    source="yfinance",
                    is_cached=False,
                    fetched_at=fetched_at
                )
            else:
                logger.warning(f"yfinance returned empty for {ticker}")
                
        except Exception as e:
            logger.warning(f"yfinance failed for {ticker}: {e}")
        
        # Record failover
        self._record_failover("yfinance", "alpha_vantage", ticker, "empty_or_error")
        
        # Try 2: AlphaVantage (secondary)
        if self._alpha_vantage:
            try:
                logger.info(f"Fetching {ticker} from AlphaVantage (failover)...")
                df = self._alpha_vantage.get_ohlcv(ticker, start_date, end_date)
                
                if not df.empty:
                    self._last_successful_source[ticker] = "alpha_vantage"
                    logger.info(f"✓ AlphaVantage success for {ticker}")
                    return DataSourceResult(
                        data=df,
                        source="alpha_vantage",
                        is_cached=False,
                        fetched_at=fetched_at
                    )
                else:
                    logger.warning(f"AlphaVantage returned empty for {ticker}")
                    
            except Exception as e:
                logger.warning(f"AlphaVantage failed for {ticker}: {e}")
            
            self._record_failover("alpha_vantage", "cache", ticker, "empty_or_error")
        else:
            logger.warning("AlphaVantage not configured, skipping")
        
        # Try 3: Cache (tertiary - degraded mode)
        cache_key = f"{ticker}_{start_date}_{end_date}_{interval}"
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            logger.info(f"✓ Cache hit for {ticker} (degraded mode)")
            return DataSourceResult(
                data=cached_result,
                source="cache",
                is_cached=True,
                fetched_at=fetched_at,
                error="Serving stale data from cache"
            )
        
        # All sources failed
        logger.error(f"All data sources failed for {ticker}")
        return DataSourceResult(
            data=pd.DataFrame(),
            source="error",
            is_cached=False,
            fetched_at=fetched_at,
            error="All data sources failed"
        )

    def get_fundamentals(self, ticker: str) -> DataSourceResult:
        """Fetch fundamentals with automatic failover.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            DataSourceResult with fundamentals dict
        """
        fetched_at = datetime.utcnow()
        
        # Try 1: yfinance
        try:
            data = self._yfinance.fetch_fundamentals(ticker)
            if data and any(v is not None for v in data.values()):
                return DataSourceResult(
                    data=data,
                    source="yfinance",
                    is_cached=False,
                    fetched_at=fetched_at
                )
        except Exception as e:
            logger.warning(f"yfinance fundamentals failed: {e}")
        
        self._record_failover("yfinance", "alpha_vantage", ticker, "fundamentals_error")
        
        # Try 2: AlphaVantage
        if self._alpha_vantage:
            try:
                data = self._alpha_vantage.get_fundamentals(ticker)
                if data and any(v is not None for v in data.values() if isinstance(v, (int, float))):
                    return DataSourceResult(
                        data=data,
                        source="alpha_vantage",
                        is_cached=False,
                        fetched_at=fetched_at
                    )
            except Exception as e:
                logger.warning(f"AlphaVantage fundamentals failed: {e}")
        
        # Return empty
        return DataSourceResult(
            data={},
            source="error",
            is_cached=False,
            fetched_at=fetched_at,
            error="Could not fetch fundamentals"
        )

    def _record_failover(
        self,
        from_source: str,
        to_source: str,
        ticker: str,
        reason: str
    ) -> None:
        """Record failover event."""
        logger.info(f"Failover: {from_source} → {to_source} ({ticker}, {reason})")
        if self._failover_metric:
            self._failover_metric.labels(
                from_source=from_source,
                to_source=to_source,
                ticker=ticker,
                reason=reason
            ).inc()

    def cache_result(
        self,
        ticker: str,
        start_date: Optional[str],
        end_date: Optional[str],
        interval: str,
        data: pd.DataFrame
    ) -> None:
        """Manually cache a result for degraded mode."""
        cache_key = f"{ticker}_{start_date}_{end_date}_{interval}"
        self._cache[cache_key] = data.copy()
        logger.debug(f"Cached result for {ticker}")

    def get_health(self) -> Dict[str, Any]:
        """Get health status of all data sources."""
        health = {
            "yfinance": {"status": "healthy"},
            "alpha_vantage": {"status": "not_configured"},
            "cache": {"entries": len(self._cache)}
        }
        
        if self._alpha_vantage:
            circuit_state = self._alpha_vantage.get_circuit_state()
            health["alpha_vantage"] = {
                "status": "healthy" if circuit_state == "closed" else "degraded",
                "circuit_state": circuit_state
            }
        
        return health

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Router cache cleared")

    def get_last_successful_source(self, ticker: str) -> Optional[str]:
        """Get last successful data source for ticker."""
        return self._last_successful_source.get(ticker)

    def get_economic_data(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> DataSourceResult:
        """Fetch economic time series data from FRED.

        Week 14: New method for macro economic queries (Fed rate, unemployment, etc.)

        Args:
            series_id: FRED series ID (e.g., "DFF", "UNRATE", "CPIAUCSL")
            start_date: Start date (YYYY-MM-DD, optional)
            end_date: End date (YYYY-MM-DD, optional)

        Returns:
            DataSourceResult with:
                - data: pd.DataFrame (DatetimeIndex, 'value' column)
                - source: "fred"
                - is_cached: bool
                - error: Optional[str]

        Examples:
            >>> router = DataSourceRouter(fred_api_key="abc123")
            >>> fed_rate = router.get_economic_data("DFF", "2024-01-01", "2024-12-31")
            >>> unemployment = router.get_economic_data("UNRATE")
        """
        fetched_at = datetime.utcnow()

        # Try FRED first
        if self._fred:
            try:
                logger.info(f"Fetching {series_id} from FRED...")
                df = self._fred.get_series(series_id, start_date, end_date)

                if df is not None and not df.empty:
                    logger.info(f"✓ FRED success for {series_id}")
                    return DataSourceResult(
                        data=df,
                        source="fred",
                        is_cached=False,
                        fetched_at=fetched_at
                    )
                else:
                    logger.warning(f"FRED returned empty for {series_id}")

            except Exception as e:
                logger.error(f"FRED failed for {series_id}: {e}")
        else:
            logger.warning("FRED not configured")

        # Fallback: Check cache
        cache_key = f"fred_{series_id}_{start_date}_{end_date}"
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            logger.info(f"✓ Cache hit for {series_id} (degraded mode)")
            return DataSourceResult(
                data=cached_result,
                source="cache",
                is_cached=True,
                fetched_at=fetched_at,
                error="Serving stale economic data from cache"
            )

        # All sources failed
        logger.error(f"All data sources failed for {series_id}")
        return DataSourceResult(
            data=pd.DataFrame(),
            source="error",
            is_cached=False,
            fetched_at=fetched_at,
            error=f"Could not fetch FRED series {series_id}"
        )
