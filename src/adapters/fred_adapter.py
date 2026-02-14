"""FRED API Adapter for Economic Data.

Week 14 Day 1: Integration of Federal Reserve Economic Data for macro queries.

Features:
- Exponential backoff retry (3 attempts)
- Circuit breaker for API resilience
- In-memory caching with 24h TTL (economic data changes slowly)
- Fallback to hardcoded rates when API unavailable
- Prometheus metrics integration

Free tier: No official limit, but use generous rate limiting (1 req/10s recommended)
API key: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import pandas as pd
import time
import os
import logging
from typing import Optional, Dict, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states (copied from AlphaVantageAdapter)."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for API resilience."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3

    def __post_init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("FRED circuit breaker: entering HALF_OPEN state")
                self.half_open_calls = 1
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return True

    def record_success(self) -> None:
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0
            logger.info("FRED circuit breaker: CLOSED (recovered)")
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("FRED circuit breaker: OPEN (recovery failed)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"FRED circuit breaker: OPEN ({self.failure_count} failures)")


class FredAdapter:
    """Federal Reserve Economic Data adapter with resilience patterns.

    Features:
    - In-memory caching with 24h TTL (economic data slow-changing)
    - Circuit breaker for resilience
    - Exponential backoff retry
    - Fallback to hardcoded recent rates (updated 2026-02-14)
    - Prometheus metrics integration

    FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
    Get API key: https://fred.stlouisfed.org/docs/api/api_key.html
    """

    # FRED has no official rate limit, but be conservative
    MIN_INTERVAL = 0.1  # 10 requests/sec max (generous)

    # Cache TTL: 24 hours (economic data changes infrequently)
    CACHE_TTL = timedelta(hours=24)

    # Retry config
    MAX_RETRIES = 3
    BASE_BACKOFF = 1.0  # seconds

    # Fallback rates (updated 2026-02-14)
    FALLBACK_RATES = {
        'DGS3MO': 4.33,     # 3-Month Treasury Constant Maturity Rate
        'DFF': 4.50,        # Federal Funds Effective Rate
        'FEDFUNDS': 4.50,   # Federal Funds Rate (target)
        'UNRATE': 3.7,      # Unemployment Rate
        'CPIAUCSL': 306.7,  # Consumer Price Index for All Urban Consumers
        'GDP': 27359.9,     # Gross Domestic Product (billions)
        'MORTGAGE30US': 6.9,  # 30-Year Fixed Rate Mortgage Average
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl_seconds: int = 86400,  # 24 hours
        cache_enabled: bool = True,
        enable_metrics: bool = True
    ):
        """Initialize FRED adapter.

        Args:
            api_key: FRED API key (or use FRED_API_KEY env var)
            cache_ttl_seconds: Cache TTL (default 24h for economic data)
            cache_enabled: Enable in-memory caching
            enable_metrics: Enable Prometheus metrics
        """
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        if not self.api_key:
            logger.warning("FRED_API_KEY not set, will use fallback rates only")

        self.cache_enabled = cache_enabled
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_metrics = enable_metrics

        # Rate limiting state
        self._last_request_time = 0.0

        # Cache: {cache_key: (data, timestamp)}
        self._cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}

        # Circuit breaker for resilience
        self._circuit = CircuitBreaker()

        # Import metrics if enabled
        if enable_metrics:
            try:
                from src.monitoring.metrics import (
                    data_source_latency_seconds,
                    data_source_errors_total,
                    cache_hit_total,
                    cache_miss_total,
                )
                self._metrics = {
                    'latency': data_source_latency_seconds,
                    'errors': data_source_errors_total,
                    'cache_hit': cache_hit_total,
                    'cache_miss': cache_miss_total,
                }
            except ImportError:
                logger.warning("Metrics module not found, disabling FRED metrics")
                self._metrics = None
        else:
            self._metrics = None

    def _rate_limit(self) -> None:
        """Enforce rate limiting (10 req/sec max)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_INTERVAL:
            sleep_time = self.MIN_INTERVAL - elapsed
            logger.debug(f"FRED rate limiting: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _get_cache_key(self, series_id: str, start_date: str, end_date: str) -> str:
        """Generate cache key for request."""
        return f"fred:{series_id}:{start_date}:{end_date}"

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Check cache for data."""
        if not self.cache_enabled:
            return None

        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            age = datetime.now() - timestamp
            if age < self.CACHE_TTL:
                logger.debug(f"FRED cache hit: {cache_key}")
                if self._metrics:
                    self._metrics['cache_hit'].labels(
                        source='fred',
                        cache_type='memory'
                    ).inc()
                return data
            else:
                logger.debug(f"FRED cache expired: {cache_key}")
                del self._cache[cache_key]

        if self._metrics:
            self._metrics['cache_miss'].labels(
                source='fred',
                cache_type='memory'
            ).inc()
        return None

    def _put_in_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """Store data in cache."""
        if self.cache_enabled:
            self._cache[cache_key] = (data, datetime.now())
            logger.debug(f"FRED cached: {cache_key}")

    def _get_fallback_data(self, series_id: str) -> pd.DataFrame:
        """Return fallback data when FRED API unavailable.

        Args:
            series_id: FRED series ID (e.g., "DGS3MO", "UNRATE")

        Returns:
            DataFrame with single row containing fallback value
        """
        fallback_value = self.FALLBACK_RATES.get(series_id, 0.0)

        logger.warning(
            f"Using FRED fallback for {series_id}: {fallback_value}"
        )

        # Return DataFrame with single row (today's date, fallback value)
        df = pd.DataFrame(
            {'value': [fallback_value]},
            index=pd.DatetimeIndex([datetime.now()])
        )
        return df

    def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Fetch economic time series from FRED.

        Args:
            series_id: FRED series ID (e.g., "DGS3MO", "UNRATE", "CPIAUCSL")
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            DataFrame with:
            - DatetimeIndex
            - 'value' column (economic indicator value)

            Falls back to hardcoded rates if API unavailable.

        Examples:
            >>> adapter = FredAdapter(api_key="abc123")
            >>> fed_rate = adapter.get_series("DFF", "2024-01-01", "2024-12-31")
            >>> unemployment = adapter.get_series("UNRATE")
        """
        # Default date range: last 1 year
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.now() - timedelta(days=365)
            start_date = start_dt.strftime("%Y-%m-%d")

        # Check cache
        cache_key = self._get_cache_key(series_id, start_date, end_date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # Check circuit breaker
        if not self._circuit.can_execute():
            logger.warning("FRED circuit breaker OPEN, using fallback")
            return self._get_fallback_data(series_id)

        # Check if API key available
        if not self.api_key:
            logger.warning("FRED API key not set, using fallback")
            return self._get_fallback_data(series_id)

        # Try API with retry
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(
                    f"FRED API attempt {attempt + 1}/{self.MAX_RETRIES} "
                    f"for {series_id} ({start_date} to {end_date})"
                )

                # Rate limit
                self._rate_limit()

                # Measure latency
                start_time = time.time()

                # Import fredapi library
                try:
                    from fredapi import Fred
                except ImportError:
                    logger.error("fredapi library not installed, using fallback")
                    return self._get_fallback_data(series_id)

                # Make API call
                fred = Fred(api_key=self.api_key)
                series = fred.get_series(
                    series_id,
                    observation_start=start_date,
                    observation_end=end_date
                )

                latency = time.time() - start_time

                # Record metrics
                if self._metrics:
                    self._metrics['latency'].labels(
                        source='fred',
                        endpoint='get_series',
                        ticker=series_id
                    ).observe(latency)

                # Convert Series to DataFrame
                if series is None or series.empty:
                    logger.warning(f"FRED returned empty data for {series_id}")
                    raise ValueError("Empty series returned")

                df = series.to_frame(name='value')

                logger.info(
                    f"FRED SUCCESS for {series_id}: {len(df)} observations, "
                    f"latest={df.iloc[-1]['value']:.2f}"
                )

                # Cache and record success
                self._put_in_cache(cache_key, df)
                self._circuit.record_success()

                return df

            except Exception as e:
                logger.warning(
                    f"FRED attempt {attempt + 1} failed for {series_id}: {e}"
                )

                if self._metrics:
                    self._metrics['errors'].labels(
                        source='fred',
                        error_type='request',
                        ticker=series_id
                    ).inc()

                # Exponential backoff
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.BASE_BACKOFF * (2 ** attempt)
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)

        # All retries failed
        logger.error(f"FRED FAILED after {self.MAX_RETRIES} attempts for {series_id}")
        self._circuit.record_failure()

        # Return fallback
        return self._get_fallback_data(series_id)

    def get_latest_value(self, series_id: str) -> Optional[float]:
        """Get the most recent value for a FRED series.

        Args:
            series_id: FRED series ID

        Returns:
            Latest value as float, or None if unavailable
        """
        try:
            df = self.get_series(series_id)
            if df is not None and not df.empty:
                return float(df.iloc[-1]['value'])
        except Exception as e:
            logger.error(f"Failed to get latest value for {series_id}: {e}")

        return None

    def get_circuit_state(self) -> str:
        """Get current circuit breaker state."""
        return self._circuit.state.value

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()
        logger.info("FRED cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'size': len(self._cache),
            'ttl_hours': self.cache_ttl_seconds / 3600,
        }
