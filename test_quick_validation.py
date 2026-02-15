#!/usr/bin/env python
"""Quick validation of ticker extraction fixes."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from eval.run_golden_set_v2 import extract_tickers_from_query

# Test 3 critical failing queries
tests = [
    ("Is Bitcoin (BTC-USD) currently above or below its 50-day moving average?", ["BTC-USD"]),
    ("What is AMD's current P/E ratio?", ["AMD"]),
    ("What is Coca-Cola's (KO) dividend yield?", ["KO"]),
]

print("=" * 60)
print("QUICK VALIDATION — 3 Critical Queries")
print("=" * 60)

for query, expected in tests:
    result = extract_tickers_from_query(query)
    status = "✅" if result[0] == expected[0] else "❌"
    print(f"{status} {query[:55]}...")
    print(f"   Expected: {expected}, Got: {result}")

print("=" * 60)
