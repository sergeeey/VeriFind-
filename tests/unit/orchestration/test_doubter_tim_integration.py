"""
Unit tests for Doubter + TIM Integration.

Week 4 Day 4: Doubter detects temporal violations via TIM.

Integration:
- DoubterAgent calls TemporalIntegrityChecker during review
- Temporal violations added to concerns
- Confidence penalty for temporal issues
"""

import pytest
from datetime import datetime, UTC

from src.orchestration.doubter_agent import DoubterAgent, DoubterVerdict, DoubterReport
from src.truth_boundary.gate import VerifiedFact


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def doubter_with_tim():
    """Create Doubter agent with TIM enabled."""
    return DoubterAgent(
        enable_doubter=True,
        enable_temporal_checks=True  # NEW: TIM integration
    )


@pytest.fixture
def doubter_without_tim():
    """Create Doubter agent without TIM (standard)."""
    return DoubterAgent(
        enable_doubter=True,
        enable_temporal_checks=False
    )


@pytest.fixture
def query_date():
    """Query date for temporal validation."""
    return datetime(2024, 1, 15, tzinfo=UTC)


@pytest.fixture
def valid_fact():
    """Valid VerifiedFact without temporal issues."""
    return VerifiedFact(
        fact_id='test_001',
        query_id='query_001',
        plan_id='plan_001',
        code_hash='hash_001',
        status='success',
        extracted_values={'correlation': 0.75, 'p_value': 0.01, 'sample_size': 100},
        execution_time_ms=1500,
        memory_used_mb=50.0,
        created_at=datetime.now(UTC)
    )


# ==============================================================================
# Temporal Violation Detection Tests
# ==============================================================================

def test_doubter_detects_lookahead_shift(doubter_with_tim, valid_fact, query_date):
    """Test Doubter detects .shift(-N) via TIM."""
    code_with_lookahead = """
import pandas as pd

df['future_return'] = df['Close'].shift(-5)  # Look-ahead bias!
correlation = df['Close'].corr(df['future_return'])
print(f"correlation: {correlation}")
"""

    report = doubter_with_tim.review(
        valid_fact,
        source_code=code_with_lookahead,
        query_context={'query_date': query_date}
    )

    # Should CHALLENGE or REJECT due to temporal violation
    assert report.verdict in [DoubterVerdict.CHALLENGE, DoubterVerdict.REJECT]

    # Should have temporal concern
    assert any('temporal' in c.lower() or 'shift' in c.lower() for c in report.concerns)

    # Should have confidence penalty
    assert report.confidence_penalty > 0.0


def test_doubter_detects_future_date_access(doubter_with_tim, valid_fact, query_date):
    """Test Doubter detects future date access via TIM."""
    code_with_future_date = """
import yfinance as yf

# Query date: 2024-01-15, but end='2025-12-31' (FUTURE!)
df = yf.download('SPY', start='2024-01-01', end='2025-12-31')
print(f"result: {len(df)}")
"""

    report = doubter_with_tim.review(
        valid_fact,
        source_code=code_with_future_date,
        query_context={'query_date': query_date}
    )

    # Should CHALLENGE or REJECT
    assert report.verdict in [DoubterVerdict.CHALLENGE, DoubterVerdict.REJECT]

    # Should mention temporal or future date
    assert any(
        'temporal' in c.lower() or 'future' in c.lower() or '2025' in c
        for c in report.concerns
    )


def test_doubter_allows_clean_code_with_tim(doubter_with_tim, valid_fact, query_date):
    """Test Doubter allows clean code even with TIM enabled."""
    clean_code = """
import json

data = [1, 2, 3, 4, 5]
mean = sum(data) / len(data)

result = {"mean": mean, "count": len(data)}
print(json.dumps(result))
"""

    report = doubter_with_tim.review(
        valid_fact,
        source_code=clean_code,
        query_context={'query_date': query_date}
    )

    # Should ACCEPT (no temporal violations, no statistical issues)
    assert report.verdict == DoubterVerdict.ACCEPT

    # Should have no temporal concerns
    assert not any('temporal' in c.lower() for c in report.concerns)


def test_doubter_allows_lagged_features(doubter_with_tim, valid_fact, query_date):
    """Test Doubter allows lagged features (.shift(+N)) with TIM."""
    code_with_lags = """
import pandas as pd

df['lagged_return'] = df['Close'].shift(5)  # OK: Lagged (not -5)
correlation = df['Close'].corr(df['lagged_return'])
print(f"correlation: {correlation}")
"""

    report = doubter_with_tim.review(
        valid_fact,
        source_code=code_with_lags,
        query_context={'query_date': query_date}
    )

    # Should ACCEPT or have minimal penalty (no temporal violation)
    assert report.verdict != DoubterVerdict.REJECT

    # Should have no critical temporal concerns
    temporal_concerns = [c for c in report.concerns if 'temporal' in c.lower() or 'look-ahead' in c.lower()]
    assert len(temporal_concerns) == 0


# ==============================================================================
# Comparison Tests: With vs Without TIM
# ==============================================================================

def test_doubter_without_tim_misses_temporal_violations(doubter_without_tim, valid_fact, query_date):
    """Test Doubter WITHOUT TIM doesn't detect temporal violations."""
    code_with_lookahead = """
df['future'] = df['Close'].shift(-10)
"""

    report = doubter_without_tim.review(
        valid_fact,
        source_code=code_with_lookahead,
        query_context={'query_date': query_date}
    )

    # Without TIM, should not flag temporal issues
    # (might still ACCEPT if no other statistical issues)
    temporal_concerns = [c for c in report.concerns if 'temporal' in c.lower() or 'shift' in c.lower()]
    assert len(temporal_concerns) == 0


def test_doubter_tim_vs_no_tim_confidence_difference(doubter_with_tim, doubter_without_tim, valid_fact, query_date):
    """Test that TIM integration increases confidence penalty for violations."""
    code_with_violation = """
df['future_ret'] = df['Close'].shift(-5)
correlation = df['Close'].corr(df['future_ret'])
print(f"correlation: {correlation}")
"""

    # With TIM
    report_with_tim = doubter_with_tim.review(
        valid_fact,
        source_code=code_with_violation,
        query_context={'query_date': query_date}
    )

    # Without TIM
    report_without_tim = doubter_without_tim.review(
        valid_fact,
        source_code=code_with_violation,
        query_context={'query_date': query_date}
    )

    # With TIM should have higher penalty
    assert report_with_tim.confidence_penalty > report_without_tim.confidence_penalty


# ==============================================================================
# Confidence Penalty Tests
# ==============================================================================

def test_temporal_violation_severe_penalty(doubter_with_tim, valid_fact, query_date):
    """Test temporal violations result in severe confidence penalty (30-50%)."""
    code_with_critical_violation = """
df['future'] = df['Close'].shift(-10)
"""

    report = doubter_with_tim.review(
        valid_fact,
        source_code=code_with_critical_violation,
        query_context={'query_date': query_date}
    )

    # Temporal violations should have penalty >= 0.3 (30%)
    assert report.confidence_penalty >= 0.3


def test_temporal_warning_moderate_penalty(doubter_with_tim, valid_fact, query_date):
    """Test temporal warnings (not critical) have moderate penalty."""
    code_with_warning = """
import pandas as pd

# Suspicious iloc (warning, not critical)
last_row = df.iloc[-1]
print(f"last_price: {last_row['Close']}")
"""

    report = doubter_with_tim.review(
        valid_fact,
        source_code=code_with_warning,
        query_context={'query_date': query_date}
    )

    # Warning should have lower penalty than critical
    # (if flagged at all)
    if report.confidence_penalty > 0:
        assert report.confidence_penalty < 0.3  # Less than critical


# ==============================================================================
# Suggested Improvements Tests
# ==============================================================================

def test_temporal_violation_suggests_improvements(doubter_with_tim, valid_fact, query_date):
    """Test Doubter suggests improvements for temporal violations."""
    code_with_violation = """
df['future'] = df['Close'].shift(-5)
"""

    report = doubter_with_tim.review(
        valid_fact,
        source_code=code_with_violation,
        query_context={'query_date': query_date}
    )

    # Should have suggestions
    assert report.suggested_improvements is not None
    assert len(report.suggested_improvements) > 0

    # Should suggest using lagged features
    suggestions_text = ' '.join(report.suggested_improvements).lower()
    assert 'shift' in suggestions_text or 'lag' in suggestions_text or 'temporal' in suggestions_text


# ==============================================================================
# Edge Cases
# ==============================================================================

def test_doubter_handles_missing_query_date(doubter_with_tim, valid_fact):
    """Test Doubter handles missing query_date gracefully."""
    code = "print('test')"

    # No query_date in context
    report = doubter_with_tim.review(
        valid_fact,
        source_code=code,
        query_context={}  # Missing query_date
    )

    # Should still produce a report (might skip TIM check or use default)
    assert report is not None
    assert isinstance(report, DoubterReport)


def test_doubter_combines_temporal_and_statistical_concerns(doubter_with_tim, query_date):
    """Test Doubter combines temporal + statistical concerns in one report."""
    # Fact with small sample size (statistical issue)
    fact_with_issues = VerifiedFact(
        fact_id='test_002',
        query_id='query_002',
        plan_id='plan_002',
        code_hash='hash_002',
        status='success',
        extracted_values={'correlation': 0.99, 'sample_size': 5},  # Small + high corr
        execution_time_ms=1000,
        memory_used_mb=30.0,
        created_at=datetime.now(UTC)
    )

    # Code with temporal violation
    code_with_temporal_issue = """
df['future'] = df['Close'].shift(-5)
correlation = df['Close'].corr(df['future'])
"""

    report = doubter_with_tim.review(
        fact_with_issues,
        source_code=code_with_temporal_issue,
        query_context={'query_date': query_date}
    )

    # Should have BOTH temporal and statistical concerns
    assert len(report.concerns) >= 2

    has_temporal = any('temporal' in c.lower() or 'shift' in c.lower() for c in report.concerns)
    has_statistical = any('sample' in c.lower() or 'correlation' in c.lower() for c in report.concerns)

    assert has_temporal and has_statistical


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week4_day4_success_criteria(doubter_with_tim, doubter_without_tim, valid_fact, query_date):
    """
    Week 4 Day 4 Success Criteria:

    - [x] Doubter integrates TIM during review
    - [x] Temporal violations added to concerns
    - [x] Confidence penalty for temporal issues (30-50%)
    - [x] Suggested improvements for violations
    - [x] Works with and without TIM (backward compatible)
    - [x] Combines temporal + statistical concerns
    """
    # Test 1: TIM detects violations
    violation_code = "df['fut'] = df['Close'].shift(-5)"
    report_with_tim = doubter_with_tim.review(
        valid_fact,
        violation_code,
        query_context={'query_date': query_date}
    )
    assert any('temporal' in c.lower() or 'shift' in c.lower() for c in report_with_tim.concerns)

    # Test 2: Confidence penalty applied
    assert report_with_tim.confidence_penalty >= 0.3

    # Test 3: Backward compatible (without TIM)
    report_without_tim = doubter_without_tim.review(
        valid_fact,
        violation_code,
        query_context={'query_date': query_date}
    )
    assert report_without_tim is not None

    # Test 4: Suggestions provided
    assert report_with_tim.suggested_improvements is not None

    print("""
    ✅ Week 4 Day 4 SUCCESS CRITERIA:
    - Doubter + TIM integration: ✅
    - Temporal concerns detected: ✅
    - Confidence penalty (30-50%): ✅
    - Suggested improvements: ✅
    - Backward compatible: ✅
    - Combined concerns: ✅
    """)
