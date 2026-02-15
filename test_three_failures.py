#!/usr/bin/env python
"""
Test ONLY 3 previously failing Golden Set queries.

gs_008: Bitcoin (BTC-USD) — was getting SPY instead
gs_014: AMD P/E ratio — was getting SPY instead
gs_026: Coca-Cola dividend — missing dividend_yield data
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env', override=True)

from eval.run_golden_set_v2 import extract_tickers_from_query, fetch_market_context


async def test_failing_queries():
    """Test 3 failing queries with REAL data fetching."""

    queries = [
        {
            "id": "gs_008",
            "query": "Is Bitcoin (BTC-USD) currently above or below its 50-day moving average?",
            "expected_ticker": "BTC-USD",
        },
        {
            "id": "gs_014",
            "query": "What is AMD's current P/E ratio?",
            "expected_ticker": "AMD",
        },
        {
            "id": "gs_026",
            "query": "What is Coca-Cola's (KO) dividend yield?",
            "expected_ticker": "KO",
        },
    ]

    print("=" * 70)
    print("TESTING 3 PREVIOUSLY FAILING QUERIES")
    print("=" * 70)

    results = []

    for q in queries:
        print(f"\n{q['id']}: {q['query'][:60]}...")

        # 1. Extract ticker
        tickers = extract_tickers_from_query(q['query'])
        print(f"  Tickers: {tickers}")

        ticker_ok = q['expected_ticker'] in tickers
        print(f"  Ticker extraction: {'✅ PASS' if ticker_ok else '❌ FAIL'}")

        # 2. Fetch data
        try:
            context = await fetch_market_context(tickers, q['query'])
            ticker_data = context['data'].get(q['expected_ticker'])

            if ticker_data:
                print(f"  Data fetched: ✅ Price=${ticker_data.get('current_price')}")

                # Special check for dividend query (gs_026)
                if q['id'] == 'gs_026':
                    div_yield = ticker_data.get('dividend_yield')
                    if div_yield:
                        print(f"  Dividend yield: ✅ {div_yield:.4f} ({div_yield*100:.2f}%)")
                    else:
                        print(f"  Dividend yield: ❌ MISSING")

                results.append({
                    'id': q['id'],
                    'ticker_extraction': 'PASS',
                    'data_fetch': 'PASS',
                    'ticker': q['expected_ticker'],
                    'price': ticker_data.get('current_price'),
                    'dividend_yield': ticker_data.get('dividend_yield'),
                })
            else:
                print(f"  Data fetched: ❌ No data for {q['expected_ticker']}")
                results.append({
                    'id': q['id'],
                    'ticker_extraction': 'PASS' if ticker_ok else 'FAIL',
                    'data_fetch': 'FAIL',
                })

        except Exception as e:
            print(f"  Error: ❌ {e}")
            results.append({
                'id': q['id'],
                'ticker_extraction': 'PASS' if ticker_ok else 'FAIL',
                'data_fetch': 'ERROR',
                'error': str(e),
            })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for r in results:
        status = "✅" if r.get('data_fetch') == 'PASS' else "❌"
        print(f"{status} {r['id']}: Ticker={r.get('ticker_extraction')}, Data={r.get('data_fetch')}")

    # Save results
    output_file = project_root / 'results' / f'three_failures_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved: {output_file}")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(test_failing_queries())
