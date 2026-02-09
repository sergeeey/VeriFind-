"""Data Adapters for APE 2026.

Week 2 Day 2: YFinance adapter for market data ingestion.
Week 11: AlphaVantage adapter with circuit breaker for production resilience.
"""

from .yfinance_adapter import YFinanceAdapter, MarketData
from .alpha_vantage_adapter import AlphaVantageAdapter, CircuitBreaker
from .data_source_router import DataSourceRouter, DataSourcePriority

__all__ = [
    "YFinanceAdapter",
    "MarketData",
    "AlphaVantageAdapter",
    "CircuitBreaker",
    "DataSourceRouter",
    "DataSourcePriority"
]
