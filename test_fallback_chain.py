import sys
import logging
from dotenv import load_dotenv
load_dotenv('.env', override=True)

# Enable logging to see fallback chain
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

sys.path.insert(0, 'src')
from adapters.yfinance_adapter_v2 import YFinanceAdapterV2

adapter = YFinanceAdapterV2(max_retries=1)  # Fast test (1 retry only)

print('\n=== Testing AAPL (should fallback to CSV) ===')
data = adapter.fetch_ohlcv('AAPL', '2024-02-01', '2024-02-14')

if data is not None and not data.empty:
    print(f'\n✅ DATA FETCHED: {len(data)} rows')
    print(f'Latest close: ${data["Close"].iloc[-1]:.2f}')
    print(f'SMA-200 equivalent: ${data["Close"].mean():.2f}')
    print(data.tail(3))
else:
    print('\n❌ FAILED - No data')
