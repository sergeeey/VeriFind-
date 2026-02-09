"""
Debug Beta calculation NaN issue.

Tests why gs_026 (AAPL beta) and gs_028 (TSLA beta) return NaN.
"""

import yfinance as yf
import pandas as pd
import numpy as np

def calculate_beta_manual(ticker: str, benchmark: str = "SPY", start: str = "2023-01-01", end: str = "2023-12-31"):
    """
    Calculate beta manually to diagnose NaN issue.

    Beta = Cov(stock, benchmark) / Var(benchmark)
    """
    print(f"\n{'='*60}")
    print(f"Calculating Beta for {ticker} vs {benchmark}")
    print(f"Period: {start} to {end}")
    print(f"{'='*60}")

    # Download data
    print(f"\n1. Downloading {ticker} data...")
    stock = yf.Ticker(ticker)
    stock_data = stock.history(start=start, end=end)
    print(f"   Rows: {len(stock_data)}, Columns: {list(stock_data.columns)}")

    print(f"\n2. Downloading {benchmark} data...")
    bench = yf.Ticker(benchmark)
    bench_data = bench.history(start=start, end=end)
    print(f"   Rows: {len(bench_data)}, Columns: {list(bench_data.columns)}")

    # Extract Close prices
    print(f"\n3. Extracting Close prices...")
    stock_close = stock_data['Close']
    bench_close = bench_data['Close']
    print(f"   {ticker} Close: {len(stock_close)} values, NaN: {stock_close.isna().sum()}")
    print(f"   {benchmark} Close: {len(bench_close)} values, NaN: {bench_close.isna().sum()}")

    # Align dates
    print(f"\n4. Aligning dates...")
    df = pd.DataFrame({'stock': stock_close, 'benchmark': bench_close}).dropna()
    print(f"   Aligned rows: {len(df)}")
    print(f"   Date range: {df.index.min()} to {df.index.max()}")

    # Calculate returns
    print(f"\n5. Calculating returns...")
    stock_returns = df['stock'].pct_change().dropna()
    bench_returns = df['benchmark'].pct_change().dropna()
    print(f"   {ticker} returns: {len(stock_returns)} values, NaN: {stock_returns.isna().sum()}")
    print(f"   {benchmark} returns: {len(bench_returns)} values, NaN: {bench_returns.isna().sum()}")
    print(f"   {ticker} returns mean: {stock_returns.mean():.6f}, std: {stock_returns.std():.6f}")
    print(f"   {benchmark} returns mean: {bench_returns.mean():.6f}, std: {bench_returns.std():.6f}")

    # Calculate covariance and variance
    print(f"\n6. Calculating covariance and variance...")
    covariance = stock_returns.cov(bench_returns)
    bench_variance = bench_returns.var()
    print(f"   Covariance: {covariance:.8f}")
    print(f"   Benchmark Variance: {bench_variance:.8f}")

    # Calculate beta
    print(f"\n7. Calculating beta...")
    if bench_variance == 0 or pd.isna(bench_variance):
        print(f"   ❌ ERROR: Benchmark variance is zero or NaN!")
        beta = np.nan
    else:
        beta = covariance / bench_variance

    print(f"   Beta: {beta:.6f}")

    # Verify with alternative method (numpy)
    print(f"\n8. Verification with numpy...")
    cov_matrix = np.cov(stock_returns, bench_returns)
    beta_numpy = cov_matrix[0, 1] / cov_matrix[1, 1]
    print(f"   Beta (numpy): {beta_numpy:.6f}")

    return beta


if __name__ == "__main__":
    # Test AAPL (gs_026 - returns NaN)
    beta_aapl = calculate_beta_manual("AAPL", "SPY")

    # Test TSLA (gs_028 - returns NaN)
    beta_tsla = calculate_beta_manual("TSLA", "SPY")

    # Test MSFT (gs_027 - works correctly)
    beta_msft = calculate_beta_manual("MSFT", "SPY")

    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    print(f"AAPL Beta: {beta_aapl:.6f} (Expected: 1.104)")
    print(f"TSLA Beta: {beta_tsla:.6f} (Expected: 2.212)")
    print(f"MSFT Beta: {beta_msft:.6f} (Expected: 1.172)")
