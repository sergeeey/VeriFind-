#!/usr/bin/env python
"""Check raw YFinance dividend data."""

import yfinance as yf

# Check raw YFinance data for KO
ticker = yf.Ticker('KO')
info = ticker.info

print('=' * 60)
print('RAW YFINANCE DATA for KO (Coca-Cola):')
print('=' * 60)
print(f'  dividendYield: {info.get("dividendYield")} (type: {type(info.get("dividendYield")).__name__})')
print(f'  dividendRate: {info.get("dividendRate")}')

# What our adapter should return
raw = info.get('dividendYield')
if raw:
    print(f'\nINTERPRETATION:')
    print(f'  Raw value: {raw}')
    print(f'  As percentage: {raw * 100:.2f}%')
    print(f'  Display: {raw:.4f} → {raw*100:.2f}%')

    if raw > 1.0:
        print(f'\n⚠️  WARNING: dividendYield > 1.0 detected!')
        print(f'  YFinance already returns percentage (not decimal)')
        print(f'  DO NOT multiply by 100 again')
    else:
        print(f'\n✅ OK: dividendYield < 1.0 (decimal format)')
        print(f'  Safe to display as {raw*100:.2f}%')
else:
    print('\n❌ dividendYield is None')

print('=' * 60)
