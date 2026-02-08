"""
Script to compute expected values for Golden Set.

This script calculates reference values for financial metrics using historical data.
These values serve as ground truth for validation testing.

Usage:
    python tests/golden_set/compute_expected_values.py

Output:
    tests/golden_set/financial_queries_v1.json
"""

import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


def calculate_sharpe_ratio(ticker: str, start_date: str, end_date: str, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe Ratio for a given ticker and period.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        risk_free_rate: Annual risk-free rate (default 2%)

    Returns:
        Sharpe ratio (annualized)
    """
    # Use Ticker API for more reliable access
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)

    if data.empty:
        raise ValueError(f"No data for {ticker} in period {start_date} to {end_date}")

    # Calculate daily returns using Close price
    returns = data['Close'].pct_change().dropna()

    # Annualize
    annual_return = returns.mean() * 252
    annual_volatility = returns.std() * np.sqrt(252)

    # Sharpe ratio
    sharpe = (annual_return - risk_free_rate) / annual_volatility

    return round(sharpe, 3)


def calculate_correlation(ticker1: str, ticker2: str, start_date: str, end_date: str) -> float:
    """Calculate correlation between two assets."""
    stock1 = yf.Ticker(ticker1)
    stock2 = yf.Ticker(ticker2)

    data1 = stock1.history(start=start_date, end=end_date)['Close']
    data2 = stock2.history(start=start_date, end=end_date)['Close']

    # Align dates
    df = pd.DataFrame({'asset1': data1, 'asset2': data2}).dropna()

    # Calculate returns
    returns1 = df['asset1'].pct_change().dropna()
    returns2 = df['asset2'].pct_change().dropna()

    correlation = returns1.corr(returns2)

    return round(correlation, 3)


def calculate_volatility(ticker: str, start_date: str, end_date: str) -> float:
    """Calculate annualized volatility."""
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)

    returns = data['Close'].pct_change().dropna()

    # Annualized volatility
    volatility = returns.std() * np.sqrt(252)

    return round(volatility, 3)


def calculate_beta(ticker: str, benchmark: str, start_date: str, end_date: str) -> float:
    """Calculate beta relative to benchmark (usually SPY)."""
    stock = yf.Ticker(ticker)
    benchmark_ticker = yf.Ticker(benchmark)

    stock_data = stock.history(start=start_date, end=end_date)['Close']
    benchmark_data = benchmark_ticker.history(start=start_date, end=end_date)['Close']

    # Align dates
    df = pd.DataFrame({'stock': stock_data, 'benchmark': benchmark_data}).dropna()

    # Calculate returns
    stock_returns = df['stock'].pct_change().dropna()
    benchmark_returns = df['benchmark'].pct_change().dropna()

    # Beta = Cov(stock, benchmark) / Var(benchmark)
    covariance = stock_returns.cov(benchmark_returns)
    benchmark_variance = benchmark_returns.var()

    beta = covariance / benchmark_variance

    return round(beta, 3)


def calculate_annual_return(ticker: str, start_date: str, end_date: str) -> float:
    """Calculate annualized return."""
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)

    start_price = data['Close'].iloc[0]
    end_price = data['Close'].iloc[-1]

    # Calculate number of years
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    years = (end_dt - start_dt).days / 365.25

    # Annualized return
    annual_return = (end_price / start_price) ** (1 / years) - 1

    return round(annual_return, 3)


def generate_golden_set() -> Dict:
    """
    Generate golden set with computed expected values.

    Returns:
        Dictionary containing all test queries with expected values
    """
    print("🔄 Computing expected values for Golden Set...")
    print("This may take 2-3 minutes (downloading historical data)...\n")

    # Use fixed reference date for reproducibility
    reference_date = "2024-01-15"

    queries = []
    query_id = 1

    # ========================================================================
    # Category 1: Sharpe Ratio (30 queries)
    # ========================================================================
    print("📊 Category 1: Sharpe Ratio (10 queries)")

    sharpe_configs = [
        ("SPY", "2023-01-01", "2023-12-31", "1 year"),
        ("SPY", "2021-01-01", "2023-12-31", "3 years"),
        ("QQQ", "2023-01-01", "2023-12-31", "1 year"),
        ("QQQ", "2021-01-01", "2023-12-31", "3 years"),
        ("AAPL", "2023-01-01", "2023-12-31", "1 year"),
        ("AAPL", "2021-01-01", "2023-12-31", "3 years"),
        ("MSFT", "2023-01-01", "2023-12-31", "1 year"),
        ("GOOGL", "2023-01-01", "2023-12-31", "1 year"),
        ("TSLA", "2023-01-01", "2023-12-31", "1 year"),
        ("VTI", "2023-01-01", "2023-12-31", "1 year"),
    ]

    for ticker, start, end, period in sharpe_configs:
        try:
            sharpe = calculate_sharpe_ratio(ticker, start, end)

            queries.append({
                "id": f"gs_{query_id:03d}",
                "category": "sharpe_ratio",
                "difficulty": "easy" if period == "1 year" else "medium",
                "query": f"Calculate the Sharpe ratio for {ticker} from {start} to {end}",
                "expected_value": sharpe,
                "tolerance": 0.15,  # ±0.15 is reasonable for Sharpe ratio
                "confidence_range": [0.85, 0.95],
                "date_computed": reference_date,
                "data_cutoff": end,
                "metric_type": "sharpe_ratio",
                "temporal_constraints": {
                    "start_date": start,
                    "end_date": end,
                    "no_future_data": True
                }
            })

            print(f"  ✅ {ticker} ({period}): Sharpe = {sharpe}")
            query_id += 1

        except Exception as e:
            print(f"  ❌ {ticker} ({period}): Error - {e}")

    # ========================================================================
    # Category 2: Correlation (10 queries)
    # ========================================================================
    print("\n📊 Category 2: Correlation (10 queries)")

    correlation_pairs = [
        ("SPY", "QQQ", "2023-01-01", "2023-12-31"),
        ("SPY", "TLT", "2023-01-01", "2023-12-31"),  # Stocks vs Bonds (negative)
        ("AAPL", "MSFT", "2023-01-01", "2023-12-31"),  # Tech stocks (high positive)
        ("XLE", "XLF", "2023-01-01", "2023-12-31"),  # Energy vs Financials
        ("GLD", "SPY", "2023-01-01", "2023-12-31"),  # Gold vs Stocks
        ("QQQ", "AAPL", "2023-01-01", "2023-12-31"),
        ("VTI", "SPY", "2023-01-01", "2023-12-31"),  # Should be ~1.0
        ("TSLA", "SPY", "2023-01-01", "2023-12-31"),
        ("BND", "SPY", "2023-01-01", "2023-12-31"),  # Bonds vs Stocks
        ("DIA", "SPY", "2023-01-01", "2023-12-31"),  # Dow vs S&P
    ]

    for ticker1, ticker2, start, end in correlation_pairs:
        try:
            corr = calculate_correlation(ticker1, ticker2, start, end)

            queries.append({
                "id": f"gs_{query_id:03d}",
                "category": "correlation",
                "difficulty": "easy",
                "query": f"What is the correlation between {ticker1} and {ticker2} from {start} to {end}?",
                "expected_value": corr,
                "tolerance": 0.10,  # ±0.10 for correlation
                "confidence_range": [0.85, 0.95],
                "date_computed": reference_date,
                "data_cutoff": end,
                "metric_type": "correlation",
                "assets": [ticker1, ticker2],
                "temporal_constraints": {
                    "start_date": start,
                    "end_date": end,
                    "no_future_data": True
                }
            })

            print(f"  ✅ {ticker1}-{ticker2}: Correlation = {corr}")
            query_id += 1

        except Exception as e:
            print(f"  ❌ {ticker1}-{ticker2}: Error - {e}")

    # ========================================================================
    # Category 3: Volatility (5 queries)
    # ========================================================================
    print("\n📊 Category 3: Volatility (5 queries)")

    volatility_configs = [
        ("SPY", "2023-01-01", "2023-12-31"),
        ("QQQ", "2023-01-01", "2023-12-31"),
        ("AAPL", "2023-01-01", "2023-12-31"),
        ("TSLA", "2023-01-01", "2023-12-31"),  # High volatility
        ("BND", "2023-01-01", "2023-12-31"),   # Low volatility
    ]

    for ticker, start, end in volatility_configs:
        try:
            vol = calculate_volatility(ticker, start, end)

            queries.append({
                "id": f"gs_{query_id:03d}",
                "category": "volatility",
                "difficulty": "easy",
                "query": f"Calculate the annualized volatility for {ticker} from {start} to {end}",
                "expected_value": vol,
                "tolerance": 0.02,  # ±0.02 (2 percentage points)
                "confidence_range": [0.85, 0.95],
                "date_computed": reference_date,
                "data_cutoff": end,
                "metric_type": "volatility",
                "temporal_constraints": {
                    "start_date": start,
                    "end_date": end,
                    "no_future_data": True
                }
            })

            print(f"  ✅ {ticker}: Volatility = {vol:.1%}")
            query_id += 1

        except Exception as e:
            print(f"  ❌ {ticker}: Error - {e}")

    # ========================================================================
    # Category 4: Beta (5 queries)
    # ========================================================================
    print("\n📊 Category 4: Beta (5 queries)")

    beta_configs = [
        ("AAPL", "SPY", "2023-01-01", "2023-12-31"),
        ("MSFT", "SPY", "2023-01-01", "2023-12-31"),
        ("TSLA", "SPY", "2023-01-01", "2023-12-31"),  # High beta
        ("KO", "SPY", "2023-01-01", "2023-12-31"),    # Low beta (defensive)
        ("QQQ", "SPY", "2023-01-01", "2023-12-31"),
    ]

    for ticker, benchmark, start, end in beta_configs:
        try:
            beta = calculate_beta(ticker, benchmark, start, end)

            queries.append({
                "id": f"gs_{query_id:03d}",
                "category": "beta",
                "difficulty": "medium",
                "query": f"Calculate the beta of {ticker} relative to {benchmark} from {start} to {end}",
                "expected_value": beta,
                "tolerance": 0.15,  # ±0.15 for beta
                "confidence_range": [0.85, 0.95],
                "date_computed": reference_date,
                "data_cutoff": end,
                "metric_type": "beta",
                "benchmark": benchmark,
                "temporal_constraints": {
                    "start_date": start,
                    "end_date": end,
                    "no_future_data": True
                }
            })

            print(f"  ✅ {ticker} vs {benchmark}: Beta = {beta}")
            query_id += 1

        except Exception as e:
            print(f"  ❌ {ticker} vs {benchmark}: Error - {e}")

    # ========================================================================
    # Metadata
    # ========================================================================
    golden_set = {
        "version": "1.0",
        "description": "Golden Set for APE 2026 - Financial Metrics Validation",
        "date_created": reference_date,
        "total_queries": len(queries),
        "categories": {
            "sharpe_ratio": len([q for q in queries if q["category"] == "sharpe_ratio"]),
            "correlation": len([q for q in queries if q["category"] == "correlation"]),
            "volatility": len([q for q in queries if q["category"] == "volatility"]),
            "beta": len([q for q in queries if q["category"] == "beta"])
        },
        "data_sources": ["yfinance"],
        "computation_method": "Python (pandas/numpy)",
        "risk_free_rate": 0.02,
        "queries": queries
    }

    print(f"\n✅ Generated {len(queries)} queries across {len(golden_set['categories'])} categories")

    return golden_set


if __name__ == "__main__":
    try:
        golden_set = generate_golden_set()

        # Save to file
        output_file = "tests/golden_set/financial_queries_v1.json"
        with open(output_file, 'w') as f:
            json.dump(golden_set, f, indent=2)

        print(f"\n✅ Golden Set saved to: {output_file}")
        print(f"\n📊 Summary:")
        print(f"  Total queries: {golden_set['total_queries']}")
        for category, count in golden_set['categories'].items():
            print(f"  {category}: {count}")

    except Exception as e:
        print(f"\n❌ Error generating Golden Set: {e}")
        import traceback
        traceback.print_exc()
