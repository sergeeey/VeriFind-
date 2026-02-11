"""Data Adapters for APE 2026.

Week 2 Day 2: YFinance adapter for market data ingestion.
Week 11 Day 1: AlphaVantage adapter with circuit breaker for production resilience.
Week 11 Day 3: Neo4j adapter for Knowledge Graph fact verification.
"""

from .yfinance_adapter import YFinanceAdapter, MarketData
from .alpha_vantage_adapter import AlphaVantageAdapter, CircuitBreaker
from .data_source_router import DataSourceRouter, DataSourcePriority
from . import neo4j_adapter

__all__ = [
    "YFinanceAdapter",
    "MarketData",
    "AlphaVantageAdapter",
    "CircuitBreaker",
    "DataSourceRouter",
    "DataSourcePriority",
    "neo4j_adapter"
]
