"""
Data Source Router with Failover Logic.

Week 11 Day 4: Cost Tracking & Reliability

Routes data requests across multiple sources with automatic failover,
circuit breaker pattern, and latency-based routing.

Priority chain: yfinance → alpha_vantage → polygon → cache → error

Author: Claude Sonnet 4.5
Created: 2026-02-08
"""

import pandas as pd
import logging
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)


class DataSourceStatus(Enum):
    """Status of a data source."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CIRCUIT_OPEN = "circuit_open"
    UNAVAILABLE = "unavailable"


@dataclass
class DataSourceMetrics:
    """Metrics for a data source."""
    source_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    circuit_breaker_failures: int = 0
    circuit_breaker_opened_at: Optional[datetime] = None
    status: DataSourceStatus = DataSourceStatus.HEALTHY

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.status == DataSourceStatus.CIRCUIT_OPEN

    def should_close_circuit(self, timeout_minutes: int = 5) -> bool:
        """Check if circuit breaker should close (half-open state)."""
        if not self.is_circuit_open():
            return False
        if self.circuit_breaker_opened_at is None:
            return True
        elapsed = datetime.now() - self.circuit_breaker_opened_at
        return elapsed > timedelta(minutes=timeout_minutes)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open for a data source."""
    pass


class DataUnavailableError(Exception):
    """Raised when all data sources have failed."""
    pass


class DataSourceRouter:
    """
    Routes data requests with automatic failover.

    Features:
    - Failover chain: yfinance → alpha_vantage → polygon → error
    - Circuit breaker: Skip failed sources for 5 minutes
    - Latency-based routing: Prefer faster sources
    - Cost optimization: Prefer free sources over paid

    Example:
        >>> router = DataSourceRouter(
        ...     yfinance=YFinanceAdapter(),
        ...     alpha_vantage=AlphaVantageAdapter(api_key="..."),
        ... )
        >>> df, source = router.get_ohlcv("AAPL", "2023-01-01", "2023-12-31")
        >>> print(f"Data from {source}: {len(df)} rows")
    """

    def __init__(
        self,
        yfinance=None,
        alpha_vantage=None,
        polygon=None,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout_minutes: int = 5,
        latency_weight: float = 0.3,
        prefer_free_sources: bool = True,
    ):
        """
        Initialize router with data sources.

        Args:
            yfinance: YFinanceAdapter instance
            alpha_vantage: AlphaVantageAdapter instance
            polygon: PolygonAdapter instance (optional)
            circuit_breaker_threshold: Failures before opening circuit (default: 5)
            circuit_breaker_timeout_minutes: Minutes before closing circuit (default: 5)
            latency_weight: Weight for latency in routing (0.0-1.0, default: 0.3)
            prefer_free_sources: Prefer free sources over paid (default: True)
        """
        self.sources = {}
        self.metrics: Dict[str, DataSourceMetrics] = {}

        # Register sources in priority order
        if yfinance:
            self._register_source("yfinance", yfinance, cost_per_call=0.0)
        if alpha_vantage:
            self._register_source("alpha_vantage", alpha_vantage, cost_per_call=0.0)
        if polygon:
            self._register_source("polygon", polygon, cost_per_call=0.002)  # $0.002/call

        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout_minutes = circuit_breaker_timeout_minutes
        self.latency_weight = latency_weight
        self.prefer_free_sources = prefer_free_sources

        if not self.sources:
            raise ValueError("At least one data source must be provided")

        logger.info(
            f"DataSourceRouter initialized with {len(self.sources)} sources: "
            f"{list(self.sources.keys())}"
        )

    def _register_source(self, name: str, adapter: Any, cost_per_call: float = 0.0):
        """Register a data source adapter."""
        self.sources[name] = {
            "adapter": adapter,
            "cost_per_call": cost_per_call,
        }
        self.metrics[name] = DataSourceMetrics(source_name=name)
        logger.debug(f"Registered source: {name} (cost: ${cost_per_call}/call)")

    def _get_source_priority(self) -> List[str]:
        """
        Get ordered list of sources by priority.

        Priority factors:
        1. Circuit breaker status (skip open circuits)
        2. Cost (prefer free if enabled)
        3. Latency (prefer faster sources)
        4. Success rate (prefer reliable sources)

        Returns:
            List of source names in priority order
        """
        candidates = []

        for name, source_info in self.sources.items():
            metrics = self.metrics[name]

            # Skip if circuit breaker is open (unless timeout expired)
            if metrics.is_circuit_open():
                if metrics.should_close_circuit(self.circuit_breaker_timeout_minutes):
                    logger.info(f"Circuit breaker for {name} entering half-open state")
                    metrics.status = DataSourceStatus.DEGRADED
                else:
                    logger.debug(f"Skipping {name}: circuit breaker open")
                    continue

            # Calculate priority score (higher = better)
            score = 0.0

            # Factor 1: Cost (free sources get +100 if prefer_free_sources)
            if self.prefer_free_sources and source_info["cost_per_call"] == 0.0:
                score += 100.0

            # Factor 2: Success rate (0-100)
            score += metrics.success_rate * 100.0

            # Factor 3: Latency (lower is better, scaled by weight)
            if metrics.avg_latency_ms > 0:
                # Penalize slow sources (max penalty: latency_weight * 100)
                latency_penalty = min(metrics.avg_latency_ms / 1000.0, 1.0) * 100.0 * self.latency_weight
                score -= latency_penalty

            candidates.append((name, score))

        # Sort by score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        priority_order = [name for name, _ in candidates]
        logger.debug(f"Source priority order: {priority_order}")

        return priority_order

    def _record_success(self, source_name: str, latency_ms: float):
        """Record successful request."""
        metrics = self.metrics[source_name]
        metrics.total_requests += 1
        metrics.successful_requests += 1
        metrics.total_latency_ms += latency_ms
        metrics.last_success = datetime.now()
        metrics.circuit_breaker_failures = 0  # Reset failures on success

        # Close circuit if was open/degraded
        if metrics.status in [DataSourceStatus.CIRCUIT_OPEN, DataSourceStatus.DEGRADED]:
            logger.info(f"Circuit breaker for {source_name} CLOSED (success)")
            metrics.status = DataSourceStatus.HEALTHY

        logger.debug(
            f"{source_name} success: {latency_ms:.2f}ms "
            f"(success_rate: {metrics.success_rate:.2%}, avg_latency: {metrics.avg_latency_ms:.2f}ms)"
        )

    def _record_failure(self, source_name: str, error: Exception):
        """Record failed request and handle circuit breaker."""
        metrics = self.metrics[source_name]
        metrics.total_requests += 1
        metrics.failed_requests += 1
        metrics.last_failure = datetime.now()
        metrics.circuit_breaker_failures += 1

        logger.warning(
            f"{source_name} failure ({metrics.circuit_breaker_failures}/{self.circuit_breaker_threshold}): "
            f"{type(error).__name__}: {error}"
        )

        # Open circuit breaker if threshold exceeded
        if metrics.circuit_breaker_failures >= self.circuit_breaker_threshold:
            metrics.status = DataSourceStatus.CIRCUIT_OPEN
            metrics.circuit_breaker_opened_at = datetime.now()
            logger.error(
                f"Circuit breaker for {source_name} OPENED "
                f"(failures: {metrics.circuit_breaker_failures})"
            )

    def get_ohlcv(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, str, float]:
        """
        Fetch OHLCV data with automatic failover.

        Args:
            ticker: Stock symbol (e.g., "AAPL")
            start_date: Start date YYYY-MM-DD (optional)
            end_date: End date YYYY-MM-DD (optional)

        Returns:
            Tuple of (DataFrame, source_name, data_freshness_timestamp)

        Raises:
            DataUnavailableError: If all sources fail

        Example:
            >>> df, source, freshness = router.get_ohlcv("AAPL")
            >>> print(f"Got {len(df)} rows from {source}")
        """
        priority_sources = self._get_source_priority()

        if not priority_sources:
            raise DataUnavailableError(
                f"No available data sources for {ticker} (all circuits open)"
            )

        errors = {}

        for source_name in priority_sources:
            adapter = self.sources[source_name]["adapter"]

            logger.info(f"Attempting to fetch {ticker} from {source_name}")

            start_time = time.time()

            try:
                # Call adapter's get_ohlcv method
                df = adapter.get_ohlcv(ticker, start_date, end_date)

                latency_ms = (time.time() - start_time) * 1000

                # Check if data is valid
                if df is None or df.empty:
                    raise ValueError(f"Empty DataFrame returned for {ticker}")

                # Success!
                self._record_success(source_name, latency_ms)

                data_freshness = time.time()

                logger.info(
                    f"Successfully fetched {ticker} from {source_name}: "
                    f"{len(df)} rows in {latency_ms:.2f}ms"
                )

                return df, source_name, data_freshness

            except Exception as e:
                self._record_failure(source_name, e)
                errors[source_name] = str(e)

                # Try next source in failover chain
                continue

        # All sources failed
        error_summary = ", ".join([f"{s}: {e}" for s, e in errors.items()])
        raise DataUnavailableError(
            f"All data sources failed for {ticker}. Errors: {error_summary}"
        )

    def get_fundamentals(
        self,
        ticker: str,
    ) -> Tuple[Dict[str, float], str, float]:
        """
        Fetch fundamental data with automatic failover.

        Args:
            ticker: Stock symbol

        Returns:
            Tuple of (fundamentals_dict, source_name, data_freshness_timestamp)

        Raises:
            DataUnavailableError: If all sources fail
        """
        priority_sources = self._get_source_priority()

        if not priority_sources:
            raise DataUnavailableError(
                f"No available data sources for {ticker} fundamentals (all circuits open)"
            )

        errors = {}

        for source_name in priority_sources:
            adapter = self.sources[source_name]["adapter"]

            # Skip if adapter doesn't support fundamentals
            if not hasattr(adapter, 'get_fundamentals'):
                logger.debug(f"{source_name} doesn't support get_fundamentals()")
                continue

            logger.info(f"Attempting to fetch {ticker} fundamentals from {source_name}")

            start_time = time.time()

            try:
                fundamentals = adapter.get_fundamentals(ticker)

                latency_ms = (time.time() - start_time) * 1000

                if not fundamentals or not isinstance(fundamentals, dict):
                    raise ValueError(f"Invalid fundamentals data for {ticker}")

                self._record_success(source_name, latency_ms)

                data_freshness = time.time()

                logger.info(
                    f"Successfully fetched {ticker} fundamentals from {source_name} "
                    f"in {latency_ms:.2f}ms"
                )

                return fundamentals, source_name, data_freshness

            except Exception as e:
                self._record_failure(source_name, e)
                errors[source_name] = str(e)
                continue

        error_summary = ", ".join([f"{s}: {e}" for s, e in errors.items()])
        raise DataUnavailableError(
            f"All data sources failed for {ticker} fundamentals. Errors: {error_summary}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get router statistics.

        Returns:
            Dict with metrics for each source:
            {
                'yfinance': {
                    'status': 'healthy',
                    'total_requests': 100,
                    'success_rate': 0.95,
                    'avg_latency_ms': 245.3,
                    ...
                },
                ...
            }
        """
        stats = {}

        for name, metrics in self.metrics.items():
            stats[name] = {
                "status": metrics.status.value,
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate": round(metrics.success_rate, 4),
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "circuit_breaker_failures": metrics.circuit_breaker_failures,
                "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
                "last_failure": metrics.last_failure.isoformat() if metrics.last_failure else None,
            }

        return stats

    def reset_circuit_breaker(self, source_name: str):
        """Manually reset circuit breaker for a source (for testing/admin)."""
        if source_name not in self.metrics:
            raise ValueError(f"Unknown source: {source_name}")

        metrics = self.metrics[source_name]
        metrics.circuit_breaker_failures = 0
        metrics.circuit_breaker_opened_at = None
        metrics.status = DataSourceStatus.HEALTHY

        logger.info(f"Circuit breaker for {source_name} manually reset")
