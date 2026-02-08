"""AlphaVantage adapter for market data fetching.

Week 11: Production-grade adapter with rate limiting, caching, and circuit breaker.

Free tier limits: 5 calls/min, 500 calls/day
Docs: https://www.alphavantage.co/documentation/
"""

import requests
import pandas as pd
import time
import logging
from typing import Optional, Dict, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
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
                logger.info("Circuit breaker: entering HALF_OPEN state")
                # Don't count the transition call, just return True for first attempt
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
            logger.info("Circuit breaker: CLOSED (recovered)")
        else:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker: OPEN (recovery failed)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker: OPEN ({self.failure_count} failures)")


class AlphaVantageAdapter:
    """Fetches market data from AlphaVantage API.
    
    Features:
    - Rate limiting: 5 calls/min (12s interval)
    - In-memory caching with 1h TTL
    - Circuit breaker for resilience
    - Exponential backoff retry
    - Prometheus metrics integration
    
    Free tier: 5 calls/min, 500 calls/day
    Get API key: https://www.alphavantage.co/support/#api-key
    """

    BASE_URL = "https://www.alphavantage.co/query"
    
    # Free tier: 60s / 5 calls = 12s between requests
    MIN_INTERVAL = 12.0
    
    # Cache TTL: 1 hour
    CACHE_TTL = timedelta(hours=1)
    
    # Retry config
    MAX_RETRIES = 3
    BASE_BACKOFF = 1.0  # seconds

    def __init__(
        self,
        api_key: str,
        cache_enabled: bool = True,
        enable_metrics: bool = True
    ):
        """Initialize adapter.
        
        Args:
            api_key: AlphaVantage API key
            cache_enabled: Enable in-memory caching
            enable_metrics: Enable Prometheus metrics
        """
        self.api_key = api_key
        self.cache_enabled = cache_enabled
        self.enable_metrics = enable_metrics
        
        # Rate limiting state
        self._last_request_time = 0.0
        
        # Cache: {cache_key: (data, timestamp)}
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        
        # Circuit breaker for resilience
        self._circuit = CircuitBreaker()
        
        # Session for connection pooling
        self._session = requests.Session()
        
        # Import metrics if enabled
        if enable_metrics:
            try:
                from src.monitoring.metrics import (
                    data_source_latency_seconds,
                    data_source_errors_total,
                    cache_hit_total,
                    cache_miss_total,
                    api_quota_remaining
                )
                self._metrics = {
                    'latency': data_source_latency_seconds,
                    'errors': data_source_errors_total,
                    'cache_hit': cache_hit_total,
                    'cache_miss': cache_miss_total,
                    'quota': api_quota_remaining
                }
            except ImportError:
                logger.warning("Metrics module not found, disabling metrics")
                self._metrics = None
        else:
            self._metrics = None

    def _rate_limit(self) -> None:
        """Enforce 5 calls/min rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_INTERVAL:
            sleep_time = self.MIN_INTERVAL - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _get_cache_key(self, function: str, symbol: str, **kwargs) -> str:
        """Generate cache key for request."""
        params = f"{function}_{symbol}_{sorted(kwargs.items())}"
        return params

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Check cache for data."""
        if not self.cache_enabled:
            return None
        
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self.CACHE_TTL:
                logger.debug(f"Cache hit: {cache_key}")
                if self._metrics:
                    self._metrics['cache_hit'].labels(
                        source='alpha_vantage',
                        cache_type='memory'
                    ).inc()
                return data
            else:
                logger.debug(f"Cache expired: {cache_key}")
                del self._cache[cache_key]
        
        if self._metrics:
            self._metrics['cache_miss'].labels(
                source='alpha_vantage',
                cache_type='memory'
            ).inc()
        return None

    def _put_in_cache(self, cache_key: str, data: Any) -> None:
        """Store data in cache."""
        if self.cache_enabled:
            self._cache[cache_key] = (data, datetime.now())
            logger.debug(f"Cached: {cache_key}")

    def _make_request(
        self,
        params: Dict[str, str],
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Make API request with retry and circuit breaker.
        
        Args:
            params: API parameters
            timeout: Request timeout in seconds
            
        Returns:
            JSON response as dict
            
        Raises:
            requests.RequestException: On persistent failure
        """
        # Check circuit breaker
        if not self._circuit.can_execute():
            raise requests.RequestException("Circuit breaker is OPEN")
        
        params['apikey'] = self.api_key
        
        for attempt in range(self.MAX_RETRIES):
            try:
                # Rate limit
                self._rate_limit()
                
                # Measure latency
                start_time = time.time()
                
                # Make request
                response = self._session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=timeout
                )
                latency = time.time() - start_time
                
                # Record metrics
                if self._metrics:
                    self._metrics['latency'].labels(
                        source='alpha_vantage',
                        endpoint=params.get('function', 'unknown'),
                        ticker=params.get('symbol', 'unknown')
                    ).observe(latency)
                
                # Check for API errors
                if response.status_code == 429:
                    raise requests.RequestException("Rate limit exceeded (429)")
                
                response.raise_for_status()
                data = response.json()
                
                # Check for AlphaVantage error messages
                if 'Error Message' in data:
                    raise requests.RequestException(f"API Error: {data['Error Message']}")
                if 'Note' in data and 'call frequency' in data['Note']:
                    raise requests.RequestException(f"Rate limit: {data['Note']}")
                
                # Success - record and return
                self._circuit.record_success()
                return data
                
            except requests.Timeout as e:
                logger.warning(f"Timeout (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if self._metrics:
                    self._metrics['errors'].labels(
                        source='alpha_vantage',
                        error_type='timeout',
                        ticker=params.get('symbol', 'unknown')
                    ).inc()
                
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.BASE_BACKOFF * (2 ** attempt)
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    self._circuit.record_failure()
                    raise
                    
            except requests.RequestException as e:
                logger.warning(f"Request error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if self._metrics:
                    self._metrics['errors'].labels(
                        source='alpha_vantage',
                        error_type='request',
                        ticker=params.get('symbol', 'unknown')
                    ).inc()
                
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.BASE_BACKOFF * (2 ** attempt)
                    time.sleep(backoff)
                else:
                    self._circuit.record_failure()
                    raise
        
        self._circuit.record_failure()
        raise requests.RequestException("Max retries exceeded")

    def get_ohlcv(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        outputsize: str = "full"
    ) -> pd.DataFrame:
        """Fetch OHLCV data from AlphaVantage.
        
        Args:
            ticker: Stock symbol (e.g., "AAPL")
            start_date: Start date YYYY-MM-DD (filters result)
            end_date: End date YYYY-MM-DD (filters result)
            outputsize: "compact" (100 days) or "full" (20+ years)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            Index: DatetimeIndex
            Empty DataFrame on error
        """
        cache_key = self._get_cache_key(
            "TIME_SERIES_DAILY",
            ticker,
            outputsize=outputsize
        )
        
        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            df = cached
        else:
            # Fetch from API
            try:
                data = self._make_request({
                    'function': 'TIME_SERIES_DAILY',
                    'symbol': ticker,
                    'outputsize': outputsize
                })
                
                # Parse time series data
                time_series_key = 'Time Series (Daily)'
                if time_series_key not in data:
                    logger.error(f"No time series data for {ticker}")
                    return pd.DataFrame()
                
                time_series = data[time_series_key]
                
                # Convert to DataFrame
                df_data = []
                for date_str, values in time_series.items():
                    df_data.append({
                        'Date': date_str,
                        'Open': float(values['1. open']),
                        'High': float(values['2. high']),
                        'Low': float(values['3. low']),
                        'Close': float(values['4. close']),
                        'Volume': int(values['5. volume'])
                    })
                
                df = pd.DataFrame(df_data)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                df.sort_index(inplace=True)
                
                # Cache result
                self._put_in_cache(cache_key, df)
                
            except Exception as e:
                logger.error(f"Failed to fetch OHLCV for {ticker}: {e}")
                return pd.DataFrame()
        
        # Filter by date range if specified
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        return df

    def get_fundamentals(self, ticker: str) -> Dict[str, Optional[float]]:
        """Fetch fundamentals from AlphaVantage OVERVIEW endpoint.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dict with fundamentals:
            - pe_ratio: P/E ratio
            - market_cap: Market capitalization
            - eps: Earnings per share
            - dividend_yield: Dividend yield
            - beta: Beta
            - week_52_high: 52 week high
            - week_52_low: 52 week low
            
            Values are None if not available
        """
        cache_key = self._get_cache_key("OVERVIEW", ticker)
        
        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            data = self._make_request({
                'function': 'OVERVIEW',
                'symbol': ticker
            })
            
            # Extract key fundamentals
            fundamentals = {
                'pe_ratio': self._safe_float(data.get('PERatio')),
                'market_cap': self._safe_float(data.get('MarketCapitalization')),
                'eps': self._safe_float(data.get('EPS')),
                'dividend_yield': self._safe_float(data.get('DividendYield')),
                'beta': self._safe_float(data.get('Beta')),
                'week_52_high': self._safe_float(data.get('52WeekHigh')),
                'week_52_low': self._safe_float(data.get('52WeekLow')),
                'sector': data.get('Sector'),
                'industry': data.get('Industry'),
            }
            
            # Cache result
            self._put_in_cache(cache_key, fundamentals)
            
            return fundamentals
            
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {ticker}: {e}")
            return {
                'pe_ratio': None,
                'market_cap': None,
                'eps': None,
                'dividend_yield': None,
                'beta': None,
                'week_52_high': None,
                'week_52_low': None,
                'sector': None,
                'industry': None,
            }

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == 'None':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_circuit_state(self) -> str:
        """Get current circuit breaker state."""
        return self._circuit.state.value

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'size': len(self._cache),
            'max_size_estimate': 500  # Rough estimate for 500 tickers
        }
