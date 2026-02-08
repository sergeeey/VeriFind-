"""
YFinance Adapter for market data ingestion.

Week 2 Day 2: Fetch OHLCV and fundamental data from Yahoo Finance.

Features:
1. OHLCV data fetching (Open, High, Low, Close, Volume)
2. Fundamental data (PE ratios, market cap, etc.)
3. In-memory caching with TTL
4. Rate limiting (basic)
5. Error handling for invalid tickers
"""

import yfinance as yf
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import time
import hashlib


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
    interval: str = '1d'  # '1d', '1h', '5m', etc.


class YFinanceAdapter:
    """
    Adapter for fetching market data from Yahoo Finance.

    Design:
    - In-memory cache with TTL to avoid redundant API calls
    - Graceful error handling for invalid tickers
    - Rate limiting (basic delay between calls)
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 3600,
        rate_limit_delay: float = 0.1
    ):
        """
        Initialize YFinance adapter.

        Args:
            cache_enabled: Enable in-memory caching
            cache_ttl_seconds: Cache time-to-live in seconds
            rate_limit_delay: Delay between API calls (seconds)
        """
        self.cache_enabled = cache_enabled
        self.cache_ttl_seconds = cache_ttl_seconds
        self.rate_limit_delay = rate_limit_delay

        # In-memory cache: {cache_key: (data, timestamp)}
        self._cache: Dict[str, tuple] = {}

        # Rate limiting
        self._last_api_call = 0.0

    def _get_cache_key(self, ticker: str, start: str, end: str, interval: str = '1d') -> str:
        """Generate cache key for request."""
        return hashlib.md5(
            f"{ticker}_{start}_{end}_{interval}".encode()
        ).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get data from cache if not expired."""
        if not self.cache_enabled:
            return None

        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            age = time.time() - timestamp

            if age < self.cache_ttl_seconds:
                return data
            else:
                # Expired - remove from cache
                del self._cache[cache_key]

        return None

    def _put_in_cache(self, cache_key: str, data: pd.DataFrame):
        """Store data in cache."""
        if self.cache_enabled:
            self._cache[cache_key] = (data, time.time())

    def _apply_rate_limit(self):
        """Apply rate limiting delay."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self._last_api_call
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)

        self._last_api_call = time.time()

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol (e.g., 'SPY', 'AAPL')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval ('1d', '1h', '5m', etc.)

        Returns:
            DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)

        Raises:
            ValueError: If dates are invalid
        """
        # Validate dates
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        if start_dt > end_dt:
            raise ValueError("start_date must be before end_date")

        # Check cache
        cache_key = self._get_cache_key(ticker, start_date, end_date, interval)
        cached_data = self._get_from_cache(cache_key)

        if cached_data is not None:
            return cached_data

        # Apply rate limiting
        self._apply_rate_limit()

        # Fetch from yfinance
        try:
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(
                start=start_date,
                end=end_date,
                interval=interval
            )

            # Store in cache
            self._put_in_cache(cache_key, data)

            return data

        except Exception as e:
            # Return empty DataFrame on error (graceful handling)
            print(f"Warning: Failed to fetch data for {ticker}: {e}")
            return pd.DataFrame()

    def fetch_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch fundamental data for ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with fundamental metrics
        """
        self._apply_rate_limit()

        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # Extract key fundamentals (with None defaults for missing)
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

            return fundamentals

        except Exception as e:
            print(f"Warning: Failed to fetch fundamentals for {ticker}: {e}")
            return {}

    def convert_to_market_data(
        self,
        df: pd.DataFrame,
        ticker: str,
        interval: str = '1d'
    ) -> List[MarketData]:
        """
        Convert DataFrame to list of MarketData objects.

        Args:
            df: DataFrame from fetch_ohlcv()
            ticker: Ticker symbol
            interval: Data interval

        Returns:
            List of MarketData objects
        """
        market_data_list = []

        for timestamp, row in df.iterrows():
            market_data = MarketData(
                ticker=ticker,
                timestamp=timestamp.to_pydatetime(),
                open_price=float(row['Open']),
                high_price=float(row['High']),
                low_price=float(row['Low']),
                close_price=float(row['Close']),
                volume=int(row['Volume']),
                interval=interval
            )
            market_data_list.append(market_data)

        return market_data_list

    def fetch_multiple(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval

        Returns:
            Dictionary mapping ticker -> DataFrame
        """
        results = {}

        for ticker in tickers:
            data = self.fetch_ohlcv(ticker, start_date, end_date, interval)
            results[ticker] = data

        return results
