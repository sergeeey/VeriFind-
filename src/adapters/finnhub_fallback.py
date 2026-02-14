"""
Finnhub Fallback Adapter — Free market data provider.

Week 13 Day 3: Fallback when YFinance fails.

Finnhub Free Tier:
- 60 API calls/minute
- Real-time quotes, historical data, fundamentals
- More reliable than Yahoo Finance

Setup:
1. Get free API key: https://finnhub.io/register
2. Add to .env: FINNHUB_API_KEY=your_key
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging
import os
import time

logger = logging.getLogger(__name__)


class FinnhubAdapter:
    """Fallback adapter for market data using Finnhub API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Finnhub adapter.

        Args:
            api_key: Finnhub API key (or from env FINNHUB_API_KEY)
        """
        self.api_key = api_key or os.getenv('FINNHUB_API_KEY')
        self.base_url = "https://finnhub.io/api/v1"

        if not self.api_key:
            logger.warning("Finnhub API key not configured")

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Finnhub.

        Args:
            ticker: Stock ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Interval (only 'D' daily supported in free tier)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        if not self.api_key:
            return None

        try:
            # Convert dates to Unix timestamps
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())

            # Finnhub candles endpoint
            url = f"{self.base_url}/stock/candle"
            params = {
                'symbol': ticker,
                'resolution': 'D',  # Daily (free tier)
                'from': start_ts,
                'to': end_ts,
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check for errors
            if data.get('s') != 'ok':
                logger.warning(f"Finnhub returned status: {data.get('s')} for {ticker}")
                return None

            # Convert to DataFrame (YFinance format)
            df = pd.DataFrame({
                'Open': data['o'],
                'High': data['h'],
                'Low': data['l'],
                'Close': data['c'],
                'Volume': data['v']
            })

            # Add timestamps as index
            df.index = pd.to_datetime(data['t'], unit='s')
            df.index.name = 'Date'

            logger.info(f"Finnhub SUCCESS for {ticker}: {len(df)} rows")
            return df

        except Exception as e:
            logger.error(f"Finnhub fetch failed for {ticker}: {e}")
            return None

    def fetch_quote(self, ticker: str) -> Optional[dict]:
        """
        Fetch real-time quote.

        Args:
            ticker: Stock ticker

        Returns:
            Dict with current price, change, etc.
        """
        if not self.api_key:
            return None

        try:
            url = f"{self.base_url}/quote"
            params = {
                'symbol': ticker,
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                'current_price': data.get('c'),
                'change': data.get('d'),
                'percent_change': data.get('dp'),
                'high': data.get('h'),
                'low': data.get('l'),
                'open': data.get('o'),
                'previous_close': data.get('pc'),
                'timestamp': data.get('t')
            }

        except Exception as e:
            logger.error(f"Finnhub quote failed for {ticker}: {e}")
            return None
