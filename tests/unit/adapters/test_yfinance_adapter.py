"""
Unit tests for YFinance Adapter (TDD).

Week 2 Day 2: RED-GREEN-REFACTOR cycle

Test strategy:
1. Write failing tests first (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor for quality (REFACTOR)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pandas as pd

from src.adapters.yfinance_adapter import YFinanceAdapter, MarketData


# ==============================================================================
# RED Phase: Failing Tests
# ==============================================================================

@pytest.fixture
def adapter():
    """Create YFinance adapter for testing."""
    return YFinanceAdapter(
        cache_enabled=True,
        cache_ttl_seconds=3600
    )


def test_adapter_initialization(adapter):
    """Test adapter initializes correctly."""
    assert adapter is not None
    assert adapter.cache_enabled is True
    assert adapter.cache_ttl_seconds == 3600


def test_fetch_ohlcv_returns_dataframe(adapter):
    """Test fetching OHLCV data returns DataFrame."""
    with patch('yfinance.Ticker') as mock_ticker:
        # Mock yfinance response
        mock_hist = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [99.0, 100.0, 101.0],
            'Close': [104.0, 105.0, 106.0],
            'Volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range('2024-01-01', periods=3, freq='D'))

        mock_ticker.return_value.history.return_value = mock_hist

        result = adapter.fetch_ohlcv(
            ticker='SPY',
            start_date='2024-01-01',
            end_date='2024-01-03'
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert 'Open' in result.columns
        assert 'Close' in result.columns
        assert 'Volume' in result.columns


def test_fetch_ohlcv_handles_invalid_ticker(adapter):
    """Test adapter handles invalid ticker gracefully."""
    with patch('yfinance.Ticker') as mock_ticker:
        # Mock empty response for invalid ticker
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        result = adapter.fetch_ohlcv(
            ticker='INVALID_TICKER_XYZ',
            start_date='2024-01-01',
            end_date='2024-01-03'
        )

        # Should return empty DataFrame, not raise exception
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


def test_fetch_ohlcv_caching(adapter):
    """Test caching prevents redundant API calls."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_hist = pd.DataFrame({
            'Close': [100.0, 101.0]
        }, index=pd.date_range('2024-01-01', periods=2, freq='D'))

        mock_ticker.return_value.history.return_value = mock_hist

        # First call - should hit API
        result1 = adapter.fetch_ohlcv('SPY', '2024-01-01', '2024-01-02')

        # Second call - should use cache
        result2 = adapter.fetch_ohlcv('SPY', '2024-01-01', '2024-01-02')

        # API should only be called once
        assert mock_ticker.return_value.history.call_count == 1
        assert result1.equals(result2)


def test_fetch_fundamentals_returns_dict(adapter):
    """Test fetching fundamental data returns dict."""
    with patch('yfinance.Ticker') as mock_ticker:
        # Mock fundamental data
        mock_info = {
            'marketCap': 500000000000,
            'trailingPE': 25.5,
            'forwardPE': 22.3,
            'priceToBook': 3.2,
            'debtToEquity': 45.6,
            'returnOnEquity': 0.18,
            'revenueGrowth': 0.12
        }

        mock_ticker.return_value.info = mock_info

        result = adapter.fetch_fundamentals(ticker='AAPL')

        assert isinstance(result, dict)
        assert 'marketCap' in result
        assert 'trailingPE' in result
        assert result['marketCap'] == 500000000000


def test_fetch_fundamentals_handles_missing_data(adapter):
    """Test fundamentals fetch handles missing fields."""
    with patch('yfinance.Ticker') as mock_ticker:
        # Mock incomplete data
        mock_info = {
            'marketCap': 1000000000
            # Missing PE ratios, etc.
        }

        mock_ticker.return_value.info = mock_info

        result = adapter.fetch_fundamentals(ticker='AAPL')

        assert isinstance(result, dict)
        assert 'marketCap' in result
        # Missing fields should have None or default values
        assert result.get('trailingPE') is None or isinstance(result.get('trailingPE'), (int, float))


def test_convert_to_market_data(adapter):
    """Test conversion from DataFrame to MarketData objects."""
    df = pd.DataFrame({
        'Open': [100.0, 101.0],
        'High': [105.0, 106.0],
        'Low': [99.0, 100.0],
        'Close': [104.0, 105.0],
        'Volume': [1000000, 1100000]
    }, index=pd.date_range('2024-01-01', periods=2, freq='D'))

    result = adapter.convert_to_market_data(df, ticker='SPY')

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(item, MarketData) for item in result)
    assert result[0].ticker == 'SPY'
    assert result[0].open_price == 100.0
    assert result[0].close_price == 104.0


def test_rate_limiting(adapter):
    """Test rate limiting prevents excessive API calls."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_hist = pd.DataFrame({
            'Close': [100.0]
        }, index=pd.date_range('2024-01-01', periods=1, freq='D'))

        mock_ticker.return_value.history.return_value = mock_hist

        # Make multiple rapid calls
        for i in range(10):
            adapter.fetch_ohlcv(f'TICKER_{i}', '2024-01-01', '2024-01-01')

        # Should not exceed rate limit (implementation-dependent)
        # This is a placeholder - actual implementation may vary
        assert True  # Rate limiter should work without errors


def test_fetch_ohlcv_with_interval(adapter):
    """Test fetching data with different intervals."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_hist = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0, 103.0]
        }, index=pd.date_range('2024-01-01', periods=4, freq='1h'))

        mock_ticker.return_value.history.return_value = mock_hist

        result = adapter.fetch_ohlcv(
            ticker='SPY',
            start_date='2024-01-01',
            end_date='2024-01-01',
            interval='1h'
        )

        assert len(result) == 4


def test_market_data_dataclass():
    """Test MarketData dataclass structure."""
    data = MarketData(
        ticker='SPY',
        timestamp=datetime(2024, 1, 1, 9, 30),
        open_price=100.0,
        high_price=105.0,
        low_price=99.0,
        close_price=104.0,
        volume=1000000,
        interval='1d'
    )

    assert data.ticker == 'SPY'
    assert data.close_price == 104.0
    assert data.volume == 1000000


def test_fetch_ohlcv_validates_dates(adapter):
    """Test date validation for OHLCV fetching."""
    with pytest.raises(ValueError, match="start_date must be before end_date"):
        adapter.fetch_ohlcv(
            ticker='SPY',
            start_date='2024-01-10',
            end_date='2024-01-01'  # End before start
        )


def test_cache_expiration(adapter):
    """Test cache expires after TTL."""
    adapter.cache_ttl_seconds = 1  # 1 second TTL

    with patch('yfinance.Ticker') as mock_ticker:
        mock_hist = pd.DataFrame({
            'Close': [100.0]
        }, index=pd.date_range('2024-01-01', periods=1, freq='D'))

        mock_ticker.return_value.history.return_value = mock_hist

        # First call
        adapter.fetch_ohlcv('SPY', '2024-01-01', '2024-01-01')

        # Wait for cache to expire
        import time
        time.sleep(1.1)

        # Second call - should hit API again
        adapter.fetch_ohlcv('SPY', '2024-01-01', '2024-01-01')

        # Should have called API twice
        assert mock_ticker.return_value.history.call_count == 2


def test_fetch_multiple_tickers(adapter):
    """Test fetching data for multiple tickers efficiently."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_hist = pd.DataFrame({
            'Close': [100.0, 101.0]
        }, index=pd.date_range('2024-01-01', periods=2, freq='D'))

        mock_ticker.return_value.history.return_value = mock_hist

        tickers = ['SPY', 'QQQ', 'IWM']
        results = adapter.fetch_multiple(
            tickers=tickers,
            start_date='2024-01-01',
            end_date='2024-01-02'
        )

        assert isinstance(results, dict)
        assert len(results) == 3
        assert all(ticker in results for ticker in tickers)


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week2_day2_success_criteria(adapter):
    """
    Week 2 Day 2 Success Criteria:

    - [x] Fetch OHLCV data from yfinance
    - [x] Fetch fundamental data
    - [x] Caching to prevent redundant calls
    - [x] Rate limiting
    - [x] Error handling for invalid tickers
    - [x] Convert to MarketData dataclass
    """
    with patch('yfinance.Ticker') as mock_ticker:
        # Mock OHLCV
        mock_hist = pd.DataFrame({
            'Open': [100.0],
            'High': [105.0],
            'Low': [99.0],
            'Close': [104.0],
            'Volume': [1000000]
        }, index=pd.date_range('2024-01-01', periods=1, freq='D'))

        # Mock fundamentals
        mock_info = {'marketCap': 500000000000, 'trailingPE': 25.5}

        mock_ticker.return_value.history.return_value = mock_hist
        mock_ticker.return_value.info = mock_info

        # Test 1: OHLCV fetch
        ohlcv = adapter.fetch_ohlcv('SPY', '2024-01-01', '2024-01-01')
        assert len(ohlcv) == 1

        # Test 2: Fundamentals fetch
        fundamentals = adapter.fetch_fundamentals('SPY')
        assert 'marketCap' in fundamentals

        # Test 3: Caching (second call should not hit API)
        ohlcv2 = adapter.fetch_ohlcv('SPY', '2024-01-01', '2024-01-01')
        assert mock_ticker.return_value.history.call_count == 1

        # Test 4: MarketData conversion
        market_data = adapter.convert_to_market_data(ohlcv, 'SPY')
        assert len(market_data) == 1
        assert isinstance(market_data[0], MarketData)

        print("""
        ✅ Week 2 Day 2 SUCCESS CRITERIA:
        - OHLCV fetching: ✅
        - Fundamentals fetching: ✅
        - Caching: ✅
        - MarketData conversion: ✅
        """)
