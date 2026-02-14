"""
YFinance Adapter v2.0 — Production-Ready with Retry + Fallback.

Week 13 Day 3: Fixes for production reliability.

Changes from v1:
1. Retry with exponential backoff (3 attempts)
2. Fallback to alternative data source (Alpha Vantage)
3. Redis caching for reliability
4. Better error handling (no silent failures)
"""

import yfinance as yf
import pandas as pd
import requests
import time
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import hashlib
import logging

# Import Finnhub fallback
try:
    from .finnhub_fallback import FinnhubAdapter
except ImportError:
    FinnhubAdapter = None

# Import CSV snapshot fallback
try:
    from .csv_snapshot_adapter import CSVSnapshotAdapter
except ImportError:
    CSVSnapshotAdapter = None

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data point (OHLCV)."""
    ticker: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    interval: str = '1d'


class YFinanceAdapterV2:
    """
    Production-ready YFinance adapter with retry + fallback.

    Features:
    - Exponential backoff retry (3 attempts)
    - Fallback to Alpha Vantage when YFinance fails
    - Redis caching (optional, falls back to in-memory)
    - Comprehensive error logging
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 3600,
        max_retries: int = 3,
        redis_client: Optional[Any] = None,
        alpha_vantage_key: Optional[str] = None
    ):
        """
        Initialize adapter.

        Args:
            cache_enabled: Enable caching
            cache_ttl_seconds: Cache TTL
            max_retries: Max retry attempts
            redis_client: Optional Redis client (falls back to in-memory)
            alpha_vantage_key: Alpha Vantage API key for fallback
        """
        self.cache_enabled = cache_enabled
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.redis_client = redis_client
        self.alpha_vantage_key = alpha_vantage_key or os.getenv('ALPHA_VANTAGE_API_KEY')

        # Finnhub fallback (more reliable than Alpha Vantage)
        self.finnhub_adapter = FinnhubAdapter() if FinnhubAdapter else None

        # CSV snapshot fallback (last resort)
        self.csv_adapter = CSVSnapshotAdapter() if CSVSnapshotAdapter else None

        # In-memory cache fallback
        self._memory_cache: Dict[str, tuple] = {}

    def _get_cache_key(self, ticker: str, start: str, end: str, interval: str = '1d') -> str:
        """Generate cache key."""
        return f"yfinance:{ticker}:{start}:{end}:{interval}"

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get from cache (Redis or in-memory)."""
        if not self.cache_enabled:
            return None

        # Try Redis first
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache HIT (Redis): {cache_key}")
                    return pd.read_json(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}, falling back to memory")

        # Fallback to in-memory
        if cache_key in self._memory_cache:
            data, timestamp = self._memory_cache[cache_key]
            age = time.time() - timestamp
            if age < self.cache_ttl_seconds:
                logger.info(f"Cache HIT (Memory): {cache_key}")
                return data
            else:
                del self._memory_cache[cache_key]

        return None

    def _put_in_cache(self, cache_key: str, data: pd.DataFrame):
        """Store in cache (Redis or in-memory)."""
        if not self.cache_enabled:
            return

        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl_seconds,
                    data.to_json()
                )
                logger.info(f"Cache WRITE (Redis): {cache_key}")
                return
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}, using memory")

        # Fallback to in-memory
        self._memory_cache[cache_key] = (data, time.time())
        logger.info(f"Cache WRITE (Memory): {cache_key}")

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Fetch OHLCV with retry + fallback.

        Strategy:
        1. Check cache
        2. Try YFinance (3 attempts with backoff)
        3. Fallback to Alpha Vantage
        4. Return empty DataFrame if all fail (with logging)

        Args:
            ticker: Stock ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval

        Returns:
            DataFrame with OHLCV data (or empty on failure)
        """
        # Check cache
        cache_key = self._get_cache_key(ticker, start_date, end_date, interval)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # Try YFinance with retry
        for attempt in range(self.max_retries):
            try:
                logger.info(f"YFinance attempt {attempt + 1}/{self.max_retries} for {ticker}")

                ticker_obj = yf.Ticker(ticker)
                data = ticker_obj.history(
                    start=start_date,
                    end=end_date,
                    interval=interval
                )

                if data is not None and not data.empty:
                    logger.info(f"YFinance SUCCESS for {ticker}: {len(data)} rows")
                    self._put_in_cache(cache_key, data)
                    return data
                else:
                    logger.warning(f"YFinance returned empty data for {ticker}")

            except Exception as e:
                logger.warning(f"YFinance attempt {attempt + 1} failed for {ticker}: {e}")

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt  # 1s, 2s, 4s
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)

        # YFinance failed after retries — try fallbacks
        logger.warning(f"YFinance FAILED after {self.max_retries} attempts for {ticker}")

        # Try Finnhub first (more reliable + free)
        if self.finnhub_adapter:
            logger.info(f"Trying Finnhub fallback for {ticker}")
            fallback_data = self.finnhub_adapter.fetch_ohlcv(ticker, start_date, end_date)
            if fallback_data is not None and not fallback_data.empty:
                logger.info(f"Finnhub SUCCESS for {ticker}")
                self._put_in_cache(cache_key, fallback_data)
                return fallback_data

        # Try Alpha Vantage as last resort
        if self.alpha_vantage_key:
            logger.info(f"Trying Alpha Vantage fallback for {ticker}")
            fallback_data = self._fetch_from_alpha_vantage(ticker, start_date, end_date)
            if fallback_data is not None and not fallback_data.empty:
                logger.info(f"Alpha Vantage SUCCESS for {ticker}")
                self._put_in_cache(cache_key, fallback_data)
                return fallback_data

        # Final fallback: CSV snapshots
        if self.csv_adapter:
            logger.warning(f"ALL EXTERNAL APIS FAILED for {ticker}. Trying CSV snapshot (last resort)")
            csv_data = self.csv_adapter.fetch_ohlcv(ticker, start_date, end_date)
            if csv_data is not None and not csv_data.empty:
                logger.warning(f"CSV snapshot SUCCESS for {ticker} (DATA MAY BE STALE)")
                self._put_in_cache(cache_key, csv_data)
                return csv_data

        # All sources failed
        logger.error(f"ALL DATA SOURCES FAILED for {ticker} (including CSV snapshots)")
        return pd.DataFrame()

    def _fetch_from_alpha_vantage(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Fallback: Fetch from Alpha Vantage.

        Docs: https://www.alphavantage.co/documentation/#daily

        Args:
            ticker: Stock ticker
            start_date: Start date (ignored for now, gets full history)
            end_date: End date (ignored for now)

        Returns:
            DataFrame in YFinance format (or None)
        """
        if not self.alpha_vantage_key:
            logger.warning("Alpha Vantage key not configured")
            return None

        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': ticker,
                'outputsize': 'full',
                'apikey': self.alpha_vantage_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check for API limit
            if 'Note' in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                return None

            # Parse time series
            if 'Time Series (Daily)' not in data:
                logger.warning(f"Alpha Vantage: No data for {ticker}")
                return None

            time_series = data['Time Series (Daily)']

            # Convert to DataFrame (YFinance format)
            rows = []
            for date_str, values in time_series.items():
                rows.append({
                    'Date': pd.to_datetime(date_str),
                    'Open': float(values['1. open']),
                    'High': float(values['2. high']),
                    'Low': float(values['3. low']),
                    'Close': float(values['4. close']),
                    'Volume': int(values['5. volume'])
                })

            df = pd.DataFrame(rows)
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)

            # Filter by date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]

            return df

        except Exception as e:
            logger.error(f"Alpha Vantage fetch failed for {ticker}: {e}")
            return None

    def fetch_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch fundamentals with retry.

        Args:
            ticker: Stock ticker

        Returns:
            Dictionary with fundamental metrics
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching fundamentals for {ticker} (attempt {attempt + 1})")

                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info

                fundamentals = {
                    'marketCap': info.get('marketCap'),
                    'trailingPE': info.get('trailingPE'),
                    'forwardPE': info.get('forwardPE'),
                    'priceToBook': info.get('priceToBook'),
                    'debtToEquity': info.get('debtToEquity'),
                    'returnOnEquity': info.get('returnOnEquity'),
                    'revenueGrowth': info.get('revenueGrowth'),
                    'earningsGrowth': info.get('earningsGrowth'),
                    'beta': info.get('beta'),
                    'dividendYield': info.get('dividendYield')
                }

                logger.info(f"Fundamentals SUCCESS for {ticker}")
                return fundamentals

            except Exception as e:
                logger.warning(f"Fundamentals attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        logger.error(f"Fundamentals FAILED for {ticker} after {self.max_retries} attempts")
        return {}
