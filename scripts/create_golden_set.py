#!/usr/bin/env python3
"""
Golden Set Creator - Ground Truth from Real Data
Uses yfinance to calculate TRUE financial metrics
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# Output to project's golden_set directory
OUTPUT_DIR = Path(__file__).parent.parent / "tests" / "golden_set" / "v2_real_data"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def calculate_sharpe_ratio(ticker, year, rf_rate):
    """Calculate Sharpe ratio from real data."""
    try:
        # Download data
        data = yf.download(ticker, start=f"{year}-01-01", end=f"{year}-12-31", progress=False)

        if len(data) < 20:
            return {"error": "Insufficient data", "value": None, "confidence": 0.0}

        # Handle MultiIndex columns (yfinance returns this for single ticker)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        # Get Close column
        close = data['Close'] if 'Close' in data.columns else data['Adj Close']

        # Calculate log returns
        returns = np.log(close / close.shift(1)).dropna()

        # Annualize
        mean_return = returns.mean() * 252
        std_return = returns.std() * np.sqrt(252)

        # Sharpe ratio
        sharpe = (mean_return - rf_rate) / std_return if std_return > 0 else 0.0

        return {
            "value": round(float(sharpe), 4),
            "confidence": 1.0,
            "data_points": len(returns),
            "mean_return": round(float(mean_return), 4),
            "volatility": round(float(std_return), 4)
        }
    except Exception as e:
        return {"error": str(e), "value": None, "confidence": 0.0}

def calculate_correlation(ticker1, ticker2, year):
    """Calculate correlation between two assets."""
    try:
        # Download data for both
        data1 = yf.download(ticker1, start=f"{year}-01-01", end=f"{year}-12-31", progress=False)
        data2 = yf.download(ticker2, start=f"{year}-01-01", end=f"{year}-12-31", progress=False)

        if len(data1) < 20 or len(data2) < 20:
            return {"error": "Insufficient data", "value": None, "confidence": 0.0}

        # Handle MultiIndex
        if isinstance(data1.columns, pd.MultiIndex):
            data1.columns = data1.columns.droplevel(1)
        if isinstance(data2.columns, pd.MultiIndex):
            data2.columns = data2.columns.droplevel(1)

        # Get Close columns
        close1 = data1['Close'] if 'Close' in data1.columns else data1['Adj Close']
        close2 = data2['Close'] if 'Close' in data2.columns else data2['Adj Close']

        # Calculate returns
        r1 = np.log(close1 / close1.shift(1))
        r2 = np.log(close2 / close2.shift(1))

        # Align dates
        combined = pd.DataFrame({
            'r1': r1,
            'r2': r2
        }).dropna()

        if len(combined) < 20:
            return {"error": "Insufficient aligned data", "value": None, "confidence": 0.0}

        # Pearson correlation
        corr = combined['r1'].corr(combined['r2'])

        return {
            "value": round(float(corr), 4),
            "confidence": 1.0,
            "data_points": len(combined)
        }
    except Exception as e:
        return {"error": str(e), "value": None, "confidence": 0.0}

def calculate_volatility(ticker, year):
    """Calculate annualized volatility."""
    try:
        data = yf.download(ticker, start=f"{year}-01-01", end=f"{year}-12-31", progress=False)

        if len(data) < 20:
            return {"error": "Insufficient data", "value": None, "confidence": 0.0}

        # Handle MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        # Get Close column
        close = data['Close'] if 'Close' in data.columns else data['Adj Close']
        returns = np.log(close / close.shift(1)).dropna()
        vol = returns.std() * np.sqrt(252)

        return {
            "value": round(float(vol), 4),
            "confidence": 1.0,
            "data_points": len(returns)
        }
    except Exception as e:
        return {"error": str(e), "value": None, "confidence": 0.0}

def calculate_beta(ticker, market, start, end):
    """Calculate Beta vs market."""
    try:
        stock = yf.download(ticker, start=start, end=end, progress=False)
        market_data = yf.download(market, start=start, end=end, progress=False)

        if len(stock) < 20 or len(market_data) < 20:
            return {"error": "Insufficient data", "value": None, "confidence": 0.0}

        # Handle MultiIndex
        if isinstance(stock.columns, pd.MultiIndex):
            stock.columns = stock.columns.droplevel(1)
        if isinstance(market_data.columns, pd.MultiIndex):
            market_data.columns = market_data.columns.droplevel(1)

        # Get Close columns
        stock_close = stock['Close'] if 'Close' in stock.columns else stock['Adj Close']
        market_close = market_data['Close'] if 'Close' in market_data.columns else market_data['Adj Close']

        # Calculate returns
        stock_returns = np.log(stock_close / stock_close.shift(1))
        market_returns = np.log(market_close / market_close.shift(1))

        # Align and calculate
        combined = pd.DataFrame({
            'stock': stock_returns,
            'market': market_returns
        }).dropna()

        if len(combined) < 20:
            return {"error": "Insufficient aligned data", "value": None, "confidence": 0.0}

        # Beta = Cov(stock, market) / Var(market)
        covariance = combined['stock'].cov(combined['market'])
        market_variance = combined['market'].var()
        beta = covariance / market_variance if market_variance > 0 else 0.0

        return {
            "value": round(float(beta), 4),
            "confidence": 1.0,
            "data_points": len(combined)
        }
    except Exception as e:
        return {"error": str(e), "value": None, "confidence": 0.0}

# Define queries
QUERIES = [
    # Sharpe (5)
    {"id": "sharpe_spy_2023", "type": "sharpe", "ticker": "SPY", "year": 2023, "rf": 0.0525},
    {"id": "sharpe_qqq_2023", "type": "sharpe", "ticker": "QQQ", "year": 2023, "rf": 0.0525},
    {"id": "sharpe_btc_2022", "type": "sharpe", "ticker": "BTC-USD", "year": 2022, "rf": 0.04},
    {"id": "sharpe_tsla_2023", "type": "sharpe", "ticker": "TSLA", "year": 2023, "rf": 0.0525},
    {"id": "sharpe_aapl_2023", "type": "sharpe", "ticker": "AAPL", "year": 2023, "rf": 0.0525},

    # Correlation (5)
    {"id": "corr_spy_qqq_2023", "type": "correlation", "t1": "SPY", "t2": "QQQ", "year": 2023},
    {"id": "corr_btc_spy_2022", "type": "correlation", "t1": "BTC-USD", "t2": "SPY", "year": 2022},
    {"id": "corr_gld_slv_2023", "type": "correlation", "t1": "GLD", "t2": "SLV", "year": 2023},
    {"id": "corr_aapl_tsla_2022", "type": "correlation", "t1": "AAPL", "t2": "TSLA", "year": 2022},
    {"id": "corr_xle_xlu_2021", "type": "correlation", "t1": "XLE", "t2": "XLU", "year": 2021},

    # Volatility (5)
    {"id": "vol_btc_2022", "type": "volatility", "ticker": "BTC-USD", "year": 2022},
    {"id": "vol_eth_2022", "type": "volatility", "ticker": "ETH-USD", "year": 2022},
    {"id": "vol_arkk_2020", "type": "volatility", "ticker": "ARKK", "year": 2020},
    {"id": "vol_tqqq_2022", "type": "volatility", "ticker": "TQQQ", "year": 2022},
    {"id": "vol_tsla_2023", "type": "volatility", "ticker": "TSLA", "year": 2023},

    # Beta (5)
    {"id": "beta_msft_2023", "type": "beta", "ticker": "MSFT", "market": "SPY", "start": "2023-01-01", "end": "2023-12-31"},
    {"id": "beta_aapl_3y", "type": "beta", "ticker": "AAPL", "market": "SPY", "start": "2020-01-01", "end": "2022-12-31"},
    {"id": "beta_tsla_2023", "type": "beta", "ticker": "TSLA", "market": "SPY", "start": "2023-01-01", "end": "2023-12-31"},
    {"id": "beta_arkk_3y", "type": "beta", "ticker": "ARKK", "market": "SPY", "start": "2020-01-01", "end": "2022-12-31"},
    {"id": "beta_btc_3y", "type": "beta", "ticker": "BTC-USD", "market": "SPY", "start": "2020-01-01", "end": "2022-12-31"},
]

def main():
    print("🔥 Golden Set Creator - Ground Truth Calculator\n")
    print(f"📊 Processing {len(QUERIES)} queries...\n")

    results = []

    for i, q in enumerate(QUERIES, 1):
        print(f"[{i}/{len(QUERIES)}] {q['id']}...", end=" ", flush=True)

        if q["type"] == "sharpe":
            result = calculate_sharpe_ratio(q["ticker"], q["year"], q["rf"])
        elif q["type"] == "correlation":
            result = calculate_correlation(q["t1"], q["t2"], q["year"])
        elif q["type"] == "volatility":
            result = calculate_volatility(q["ticker"], q["year"])
        elif q["type"] == "beta":
            result = calculate_beta(q["ticker"], q["market"], q["start"], q["end"])
        else:
            result = {"error": "Unknown type", "value": None, "confidence": 0.0}

        # Add query metadata
        result_entry = {
            "query_id": q["id"],
            "type": q["type"],
            "query_params": {k: v for k, v in q.items() if k not in ["id", "type"]},
            **result
        }

        results.append(result_entry)

        if result.get("value") is not None:
            print(f"✅ {result['value']:.4f}")
        else:
            print(f"❌ {result.get('error', 'Failed')}")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"golden_set_{timestamp}.json"

    output_data = {
        "metadata": {
            "created_at": timestamp,
            "total_queries": len(QUERIES),
            "successful": sum(1 for r in results if r.get("value") is not None),
            "source": "yfinance",
            "description": "Ground truth calculated from real market data"
        },
        "results": results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Golden Set created: {output_file}")
    print(f"📈 Success rate: {output_data['metadata']['successful']}/{len(QUERIES)}")

    # Summary by type
    print("\n📊 Summary by type:")
    for metric_type in ["sharpe", "correlation", "volatility", "beta"]:
        type_results = [r for r in results if r["type"] == metric_type]
        successful = sum(1 for r in type_results if r.get("value") is not None)
        print(f"  {metric_type}: {successful}/{len(type_results)} successful")

if __name__ == "__main__":
    main()
