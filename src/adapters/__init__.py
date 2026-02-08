"""
Data Adapters for APE 2026.

Week 2 Day 2: YFinance adapter for market data ingestion.
"""

from .yfinance_adapter import YFinanceAdapter, MarketData

__all__ = ["YFinanceAdapter", "MarketData"]
