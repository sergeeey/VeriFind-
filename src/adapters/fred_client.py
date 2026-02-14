"""
FRED (Federal Reserve Economic Data) API Client.

Week 14 Day 2: Fetch macroeconomic indicators from St. Louis Fed.

Free API key required: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FREDDataPoint:
    """Single economic indicator data point."""
    indicator: str
    value: float
    date: datetime
    units: str
    source: str = "FRED"


class FREDClient:
    """
    Client for FRED (Federal Reserve Economic Data) API.

    Usage:
        client = FREDClient(api_key=os.getenv("FRED_API_KEY"))
        fed_rate = await client.get_latest("DFF")  # Federal Funds Rate
        unemployment = await client.get_latest("UNRATE")  # Unemployment Rate
    """

    # Common economic indicators
    INDICATORS = {
        "fed_rate": "DFF",           # Federal Funds Effective Rate (daily)
        "unemployment": "UNRATE",    # Unemployment Rate (monthly)
        "inflation": "CPIAUCSL",     # Consumer Price Index (monthly)
        "gdp": "GDP",                # Gross Domestic Product (quarterly)
        "t10y": "DGS10",             # 10-Year Treasury Constant Maturity Rate
        "t3m": "DGS3MO",             # 3-Month Treasury Constant Maturity Rate
        "pce": "PCE",                # Personal Consumption Expenditures
        "m2": "M2SL",                # M2 Money Stock
    }

    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FRED API client.

        Args:
            api_key: FRED API key (or set FRED_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        if not self.api_key:
            logger.warning("FRED_API_KEY not set. Using fallback values.")
            self.use_fallback = True
        else:
            self.use_fallback = False

        # Fallback values (last known as of 2026-02-14)
        self.fallback_values = {
            "DFF": 4.33,       # Fed Funds Rate
            "UNRATE": 3.7,     # Unemployment Rate
            "CPIAUCSL": 315.0, # CPI (not growth rate, absolute index)
            "DGS10": 4.25,     # 10-Year Treasury
            "DGS3MO": 4.50,    # 3-Month Treasury
        }

    async def get_latest(
        self,
        series_id: str,
        fallback_value: Optional[float] = None
    ) -> FREDDataPoint:
        """
        Get latest value for economic indicator.

        Args:
            series_id: FRED series ID (e.g., "DFF", "UNRATE")
            fallback_value: Value to use if API fails

        Returns:
            FREDDataPoint with latest value

        Raises:
            ValueError: If API fails and no fallback provided
        """
        # Use fallback if no API key
        if self.use_fallback:
            value = fallback_value or self.fallback_values.get(series_id)
            if value is None:
                raise ValueError(f"No API key and no fallback value for {series_id}")

            logger.info(f"Using fallback value for {series_id}: {value}")
            return FREDDataPoint(
                indicator=series_id,
                value=value,
                date=datetime.now(),
                units="Fallback",
                source="FRED (fallback)"
            )

        # Fetch from API
        try:
            async with aiohttp.ClientSession() as session:
                # Get series metadata for units
                metadata_url = f"{self.BASE_URL}/series"
                metadata_params = {
                    "series_id": series_id,
                    "api_key": self.api_key,
                    "file_type": "json"
                }

                async with session.get(metadata_url, params=metadata_params) as response:
                    response.raise_for_status()
                    metadata = await response.json()
                    units = metadata.get("seriess", [{}])[0].get("units", "Unknown")

                # Get latest observation
                obs_url = f"{self.BASE_URL}/series/observations"
                obs_params = {
                    "series_id": series_id,
                    "api_key": self.api_key,
                    "file_type": "json",
                    "sort_order": "desc",  # Latest first
                    "limit": 1
                }

                async with session.get(obs_url, params=obs_params) as response:
                    response.raise_for_status()
                    data = await response.json()

                    observations = data.get("observations", [])
                    if not observations:
                        raise ValueError(f"No observations found for {series_id}")

                    latest = observations[0]
                    value = float(latest["value"])
                    date_str = latest["date"]

                    return FREDDataPoint(
                        indicator=series_id,
                        value=value,
                        date=datetime.fromisoformat(date_str),
                        units=units,
                        source="FRED API"
                    )

        except Exception as e:
            logger.error(f"FRED API error for {series_id}: {e}")

            # Use fallback if available
            fallback = fallback_value or self.fallback_values.get(series_id)
            if fallback is not None:
                logger.warning(f"Using fallback value for {series_id}: {fallback}")
                return FREDDataPoint(
                    indicator=series_id,
                    value=fallback,
                    date=datetime.now(),
                    units="Fallback (API error)",
                    source="FRED (fallback after error)"
                )

            raise ValueError(f"FRED API failed for {series_id} and no fallback available") from e

    async def get_multiple(
        self,
        series_ids: List[str],
        fallback_values: Optional[Dict[str, float]] = None
    ) -> Dict[str, FREDDataPoint]:
        """
        Get multiple indicators at once.

        Args:
            series_ids: List of FRED series IDs
            fallback_values: Dict of fallback values

        Returns:
            Dict mapping series_id to FREDDataPoint
        """
        fallback_values = fallback_values or {}
        results = {}

        for series_id in series_ids:
            fallback = fallback_values.get(series_id)
            try:
                results[series_id] = await self.get_latest(series_id, fallback)
            except Exception as e:
                logger.error(f"Failed to fetch {series_id}: {e}")
                # Skip this indicator if it fails
                continue

        return results

    async def get_common_indicators(self) -> Dict[str, FREDDataPoint]:
        """
        Get all common economic indicators.

        Returns:
            Dict mapping indicator name to FREDDataPoint
        """
        series_ids = list(self.INDICATORS.values())
        raw_results = await self.get_multiple(series_ids)

        # Map back to common names
        results = {}
        for name, series_id in self.INDICATORS.items():
            if series_id in raw_results:
                results[name] = raw_results[series_id]

        return results


# Convenience function for quick access
async def get_fred_indicator(
    indicator: str,
    api_key: Optional[str] = None,
    fallback: Optional[float] = None
) -> float:
    """
    Quick helper to get single indicator value.

    Args:
        indicator: Series ID or common name (e.g., "DFF" or "fed_rate")
        api_key: FRED API key (optional)
        fallback: Fallback value if API fails

    Returns:
        Latest indicator value (float)

    Example:
        fed_rate = await get_fred_indicator("fed_rate")
        unemployment = await get_fred_indicator("UNRATE", fallback=3.7)
    """
    client = FREDClient(api_key=api_key)

    # Map common name to series ID
    series_id = FREDClient.INDICATORS.get(indicator, indicator)

    data_point = await client.get_latest(series_id, fallback)
    return data_point.value
