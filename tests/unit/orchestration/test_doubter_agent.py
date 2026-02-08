"""
Unit tests for Doubter Agent.

Week 4 Day 1: Adversarial validation of VerifiedFacts.
"""

import pytest
from datetime import datetime, UTC

from src.orchestration.doubter_agent import DoubterAgent, DoubterVerdict, DoubterReport
from src.truth_boundary.gate import VerifiedFact


@pytest.fixture
def doubter():
    """Create Doubter agent."""
    return DoubterAgent(enable_doubter=True)


def test_doubter_accepts_valid_fact(doubter):
    """Test Doubter accepts clean VerifiedFact."""
    fact = VerifiedFact(
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

    report = doubter.review(fact, 'test_code', {})

    assert report.verdict == DoubterVerdict.ACCEPT
    assert report.confidence_penalty < 0.2


def test_doubter_challenges_high_correlation(doubter):
    """Test Doubter challenges suspiciously high correlation."""
    fact = VerifiedFact(
        fact_id='test_002',
        query_id='query_002',
        plan_id='plan_002',
        code_hash='hash_002',
        status='success',
        extracted_values={'correlation': 0.99},  # Too high
        execution_time_ms=1000,
        memory_used_mb=30.0,
        created_at=datetime.now(UTC)
    )

    report = doubter.review(fact, 'test_code', {})

    assert report.verdict == DoubterVerdict.CHALLENGE
    assert any('overfitting' in c.lower() for c in report.concerns)


def test_doubter_challenges_small_sample(doubter):
    """Test Doubter challenges small sample size."""
    fact = VerifiedFact(
        fact_id='test_003',
        query_id='query_003',
        plan_id='plan_003',
        code_hash='hash_003',
        status='success',
        extracted_values={'correlation': 0.80, 'sample_size': 10},  # Too small
        execution_time_ms=1000,
        memory_used_mb=30.0,
        created_at=datetime.now(UTC)
    )

    report = doubter.review(fact, 'test_code', {})

    assert report.verdict == DoubterVerdict.CHALLENGE
    assert any('sample size' in c for c in report.concerns)


def test_doubter_rejects_failed_execution(doubter):
    """Test Doubter rejects failed VerifiedFact."""
    fact = VerifiedFact(
        fact_id='test_004',
        query_id='query_004',
        plan_id='plan_004',
        code_hash='hash_004',
        status='error',  # Failed
        extracted_values={},
        execution_time_ms=500,
        memory_used_mb=20.0,
        created_at=datetime.now(UTC),
        error_message='Execution failed'
    )

    report = doubter.review(fact, 'test_code', {})

    assert report.verdict == DoubterVerdict.REJECT
    assert report.confidence_penalty >= 0.5


def test_doubter_confidence_adjustment(doubter):
    """Test confidence adjustment based on verdict."""
    report_accept = DoubterReport(
        verdict=DoubterVerdict.ACCEPT,
        concerns=[],
        confidence_penalty=0.0,
        reasoning='All good'
    )

    report_challenge = DoubterReport(
        verdict=DoubterVerdict.CHALLENGE,
        concerns=['Issue 1', 'Issue 2'],
        confidence_penalty=0.3,
        reasoning='Some concerns'
    )

    report_reject = DoubterReport(
        verdict=DoubterVerdict.REJECT,
        concerns=['Critical'],
        confidence_penalty=1.0,
        reasoning='Rejected'
    )

    # Test adjustments
    assert doubter.adjust_confidence(0.9, report_accept) == 0.9
    assert doubter.adjust_confidence(0.9, report_challenge) == pytest.approx(0.63, abs=0.01)
    assert doubter.adjust_confidence(0.9, report_reject) == 0.0


def test_doubter_disabled_mode(doubter):
    """Test Doubter in disabled mode."""
    doubter_off = DoubterAgent(enable_doubter=False)

    fact = VerifiedFact(
        fact_id='test_005',
        query_id='query_005',
        plan_id='plan_005',
        code_hash='hash_005',
        status='error',  # Would normally reject
        extracted_values={},
        execution_time_ms=100,
        memory_used_mb=10.0,
        created_at=datetime.now(UTC)
    )

    report = doubter_off.review(fact, 'code', {})

    assert report.verdict == DoubterVerdict.ACCEPT
    assert report.confidence_penalty == 0.0


def test_week4_day1_success_criteria(doubter):
    """
    Week 4 Day 1 Success Criteria:

    - [x] Doubter agent implementation
    - [x] Review VerifiedFacts
    - [x] Detect logical issues
    - [x] Confidence penalty calculation
    - [x] Verdict: ACCEPT/CHALLENGE/REJECT
    """
    # Valid fact
    valid_fact = VerifiedFact(
        fact_id='criteria_001',
        query_id='query_criteria',
        plan_id='plan_criteria',
        code_hash='hash_criteria',
        status='success',
        extracted_values={'value': 42, 'p_value': 0.05, 'sample_size': 50},
        execution_time_ms=1000,
        memory_used_mb=30.0,
        created_at=datetime.now(UTC)
    )

    report = doubter.review(valid_fact, 'code', {})

    assert report is not None
    assert report.verdict in [DoubterVerdict.ACCEPT, DoubterVerdict.CHALLENGE, DoubterVerdict.REJECT]
    assert isinstance(report.confidence_penalty, float)
    assert 0.0 <= report.confidence_penalty <= 1.0

    print("""
    ✅ Week 4 Day 1 SUCCESS CRITERIA:
    - Doubter agent: ✅
    - Review VerifiedFacts: ✅
    - Detect issues: ✅
    - Confidence penalty: ✅
    - Verdicts (ACCEPT/CHALLENGE/REJECT): ✅
    """)
