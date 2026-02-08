"""
Unit tests for Temporal Integrity Module (TIM).

Week 4 Day 3: Prevent look-ahead bias in backtesting.

TIM validates VEE code for temporal violations:
1. .shift(-N) calls (future data access)
2. Date ranges (query_date <= max(data dates))
3. Suspicious operations (df.iloc[-1] without context)
"""

import pytest
from datetime import datetime, timedelta, UTC

from src.temporal.integrity_checker import (
    TemporalIntegrityChecker,
    TemporalViolation,
    ViolationType,
    TemporalCheckResult
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def tim():
    """Create Temporal Integrity Checker."""
    return TemporalIntegrityChecker(enable_checks=True)


@pytest.fixture
def query_date():
    """Query date for temporal validation."""
    return datetime(2024, 1, 15, tzinfo=UTC)


# ==============================================================================
# Look-Ahead Bias Detection Tests
# ==============================================================================

def test_detect_shift_negative_lookahead(tim, query_date):
    """Test TIM detects .shift(-N) as look-ahead bias."""
    code = """
import pandas as pd

df['future_return'] = df['Close'].shift(-5)  # VIOLATION: Look-ahead
correlation = df['Close'].corr(df['future_return'])
print(f"correlation: {correlation}")
"""

    result = tim.check_code(code, query_date=query_date)

    assert result.has_violations is True
    assert len(result.violations) >= 1

    # Should detect shift(-5) as look-ahead
    shift_violation = next(
        (v for v in result.violations if v.violation_type == ViolationType.LOOK_AHEAD_SHIFT),
        None
    )
    assert shift_violation is not None
    assert 'shift(-5)' in shift_violation.description or '-5' in shift_violation.description


def test_allow_shift_positive_lagged(tim, query_date):
    """Test TIM allows .shift(+N) as valid lagged features."""
    code = """
import pandas as pd

df['lagged_return'] = df['Close'].shift(5)  # OK: Lagged feature
correlation = df['Close'].corr(df['lagged_return'])
"""

    result = tim.check_code(code, query_date=query_date)

    # Should NOT flag positive shift as violation
    assert result.has_violations is False or all(
        v.violation_type != ViolationType.LOOK_AHEAD_SHIFT
        for v in result.violations
    )


def test_detect_iloc_negative_index_without_context(tim, query_date):
    """Test TIM detects df.iloc[-1] as potential look-ahead."""
    code = """
import pandas as pd

# Get last row (could be future if data not filtered by date)
last_price = df.iloc[-1]['Close']
print(f"price: {last_price}")
"""

    result = tim.check_code(code, query_date=query_date)

    # Should flag suspicious iloc[-1] usage
    assert result.has_violations is True
    iloc_violation = next(
        (v for v in result.violations if v.violation_type == ViolationType.SUSPICIOUS_ILOC),
        None
    )
    assert iloc_violation is not None


def test_allow_iloc_with_date_filter(tim, query_date):
    """Test TIM allows df.iloc[-1] if data filtered by date first."""
    code = """
import pandas as pd

# Filter by date FIRST (safe)
df_filtered = df[df.index <= '2024-01-15']
last_price = df_filtered.iloc[-1]['Close']  # OK: Filtered data
"""

    result = tim.check_code(code, query_date=query_date)

    # Should allow if date filtering present (heuristic)
    # This is a complex check, so we allow warnings but not hard violations
    if result.has_violations:
        assert all(
            v.severity != 'critical'
            for v in result.violations
            if v.violation_type == ViolationType.SUSPICIOUS_ILOC
        )


def test_detect_future_date_access(tim, query_date):
    """Test TIM detects date ranges exceeding query_date."""
    code = """
import yfinance as yf

# Query date: 2024-01-15
# BUT end_date is 2024-12-31 (FUTURE!)
df = yf.download('SPY', start='2024-01-01', end='2024-12-31')
"""

    result = tim.check_code(code, query_date=query_date)

    assert result.has_violations is True

    # Should detect future date access
    date_violation = next(
        (v for v in result.violations if v.violation_type == ViolationType.FUTURE_DATE_ACCESS),
        None
    )
    assert date_violation is not None
    assert '2024-12-31' in date_violation.description


def test_allow_past_date_range(tim, query_date):
    """Test TIM allows date ranges before query_date."""
    code = """
import yfinance as yf

# Query date: 2024-01-15
# Date range: 2023-01-01 to 2024-01-10 (PAST - OK)
df = yf.download('SPY', start='2023-01-01', end='2024-01-10')
"""

    result = tim.check_code(code, query_date=query_date)

    # Should NOT flag past dates
    assert result.has_violations is False or all(
        v.violation_type != ViolationType.FUTURE_DATE_ACCESS
        for v in result.violations
    )


# ==============================================================================
# Complex Pattern Detection
# ==============================================================================

def test_detect_rolling_window_lookahead(tim, query_date):
    """Test TIM detects rolling windows using future data."""
    code = """
import pandas as pd

# Rolling mean using FUTURE data (center=True with min_periods issue)
df['ma_future'] = df['Close'].rolling(window=10, center=True).mean()
"""

    result = tim.check_code(code, query_date=query_date)

    # Should warn about centered rolling (uses future data)
    assert result.has_violations is True
    rolling_violation = next(
        (v for v in result.violations if 'rolling' in v.description.lower()),
        None
    )
    assert rolling_violation is not None


def test_allow_rolling_window_past_only(tim, query_date):
    """Test TIM allows rolling windows using only past data."""
    code = """
import pandas as pd

# Rolling mean using PAST data only (default: center=False)
df['ma_past'] = df['Close'].rolling(window=10).mean()
"""

    result = tim.check_code(code, query_date=query_date)

    # Should allow backward-looking rolling
    assert result.has_violations is False or all(
        'rolling' not in v.description.lower()
        for v in result.violations
    )


def test_detect_multiple_violations(tim, query_date):
    """Test TIM detects multiple violations in one code block."""
    code = """
import yfinance as yf
import pandas as pd

# Violation 1: Future date
df = yf.download('SPY', start='2024-01-01', end='2024-12-31')

# Violation 2: Look-ahead shift
df['future_ret'] = df['Close'].shift(-5)

# Violation 3: Suspicious iloc
last_price = df.iloc[-1]['Close']

print(df.head())
"""

    result = tim.check_code(code, query_date=query_date)

    assert result.has_violations is True
    assert len(result.violations) >= 3

    # Check all violation types present
    violation_types = {v.violation_type for v in result.violations}
    assert ViolationType.FUTURE_DATE_ACCESS in violation_types
    assert ViolationType.LOOK_AHEAD_SHIFT in violation_types
    assert ViolationType.SUSPICIOUS_ILOC in violation_types


# ==============================================================================
# Edge Cases and Valid Code
# ==============================================================================

def test_allow_clean_code_no_violations(tim, query_date):
    """Test TIM allows clean code without temporal issues."""
    code = """
import pandas as pd
import yfinance as yf

# Valid: Past date range
df = yf.download('SPY', start='2023-01-01', end='2024-01-14')

# Valid: Lagged features
df['return'] = df['Close'].pct_change()
df['lagged_return'] = df['return'].shift(1)

# Valid: Backward rolling
df['ma_20'] = df['Close'].rolling(20).mean()

# Calculate correlation
correlation = df['return'].corr(df['lagged_return'])
print(f"correlation: {correlation}")
"""

    result = tim.check_code(code, query_date=query_date)

    assert result.has_violations is False
    assert len(result.violations) == 0


def test_handle_code_without_dates(tim, query_date):
    """Test TIM handles code without date operations."""
    code = """
import json

# Pure calculation, no temporal aspect
data = [1, 2, 3, 4, 5]
mean = sum(data) / len(data)

result = {"mean": mean}
print(json.dumps(result))
"""

    result = tim.check_code(code, query_date=query_date)

    # Should pass (no temporal operations)
    assert result.has_violations is False


def test_disabled_mode_allows_all(query_date):
    """Test TIM in disabled mode allows all code."""
    tim_disabled = TemporalIntegrityChecker(enable_checks=False)

    # Code with obvious violations
    code = """
df['future'] = df['Close'].shift(-10)
df = yf.download('SPY', end='2030-12-31')
"""

    result = tim_disabled.check_code(code, query_date=query_date)

    # Disabled mode should not flag violations
    assert result.has_violations is False


# ==============================================================================
# Integration with VerifiedFact
# ==============================================================================

def test_generate_temporal_report(tim, query_date):
    """Test TIM generates detailed temporal report."""
    code = """
df['future_ret'] = df['Close'].shift(-5)
last_price = df.iloc[-1]['Close']
"""

    result = tim.check_code(code, query_date=query_date)

    # Should have detailed report
    assert result.report is not None
    assert len(result.report) > 50  # Non-trivial description

    # Should include violation details
    for violation in result.violations:
        assert violation.line_number is not None
        assert violation.description is not None
        assert violation.severity in ['warning', 'critical']


def test_severity_levels(tim, query_date):
    """Test TIM assigns correct severity levels."""
    # Critical: Future date access
    critical_code = """
df = yf.download('SPY', end='2025-12-31')
"""

    critical_result = tim.check_code(critical_code, query_date=query_date)
    critical_violations = [v for v in critical_result.violations if v.severity == 'critical']
    assert len(critical_violations) > 0

    # Warning: Suspicious iloc (might be OK with filtering)
    warning_code = """
last_row = df.iloc[-1]
"""

    warning_result = tim.check_code(warning_code, query_date=query_date)
    warning_violations = [v for v in warning_result.violations if v.severity == 'warning']
    assert len(warning_violations) > 0


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week4_day3_success_criteria(tim, query_date):
    """
    Week 4 Day 3 Success Criteria:

    - [x] TIM detects look-ahead bias (.shift(-N))
    - [x] TIM detects future date access
    - [x] TIM detects suspicious iloc usage
    - [x] TIM allows valid lagged features
    - [x] TIM allows past date ranges
    - [x] TIM handles multiple violations
    - [x] TIM generates detailed reports
    - [x] Severity levels (warning vs critical)
    """
    # Test 1: Detect look-ahead shift
    lookahead_code = "df['fut'] = df['Close'].shift(-5)"
    lookahead_result = tim.check_code(lookahead_code, query_date)
    assert lookahead_result.has_violations is True

    # Test 2: Detect future date
    future_date_code = "df = yf.download('SPY', end='2025-12-31')"
    future_result = tim.check_code(future_date_code, query_date)
    assert future_result.has_violations is True

    # Test 3: Allow lagged features
    lagged_code = "df['lag'] = df['Close'].shift(5)"
    lagged_result = tim.check_code(lagged_code, query_date)
    assert lagged_result.has_violations is False

    # Test 4: Allow past dates
    past_code = "df = yf.download('SPY', end='2024-01-10')"
    past_result = tim.check_code(past_code, query_date)
    assert past_result.has_violations is False

    print("""
    ✅ Week 4 Day 3 SUCCESS CRITERIA:
    - Detect look-ahead shift: ✅
    - Detect future date access: ✅
    - Detect suspicious operations: ✅
    - Allow valid patterns: ✅
    - Severity levels: ✅
    - Detailed reports: ✅
    - TIM functional: ✅
    """)
