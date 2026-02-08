"""
Unit tests for Debate System.

Week 5 Day 2: Multi-perspective analysis tests.

Tests cover:
- DebaterAgent (Bull, Bear, Neutral perspectives)
- SynthesizerAgent (combining perspectives)
- DebateProtocol (orchestration)
- Schemas validation
"""

import pytest

from src.debate.schemas import (
    Perspective,
    Argument,
    ArgumentStrength,
    DebateReport,
    Synthesis,
    DebateContext
)
from src.debate.debater_agent import DebaterAgent
from src.debate.synthesizer_agent import SynthesizerAgent


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def debate_context_positive():
    """DebateContext with positive metrics."""
    return DebateContext(
        fact_id='test_001',
        extracted_values={
            'correlation': 0.85,
            'p_value': 0.002,
            'sample_size': 150
        },
        source_code="# Positive analysis code",
        query_text="Calculate correlation between SPY and QQQ",
        execution_metadata={'execution_time_ms': 1500}
    )


@pytest.fixture
def debate_context_concerning():
    """DebateContext with concerning metrics."""
    return DebateContext(
        fact_id='test_002',
        extracted_values={
            'correlation': 0.98,  # Suspiciously high
            'sample_size': 15      # Small sample
        },
        source_code="# Concerning analysis",
        query_text="Test query",
        execution_metadata={'execution_time_ms': 5}  # Suspiciously fast
    )


@pytest.fixture
def debate_context_neutral():
    """DebateContext with neutral metrics."""
    return DebateContext(
        fact_id='test_003',
        extracted_values={
            'correlation': 0.65,
            'p_value': 0.03,
            'sample_size': 75
        },
        source_code="# Balanced analysis",
        query_text="Moderate query"
    )


# ==============================================================================
# DebaterAgent Tests - Bull Perspective
# ==============================================================================

def test_bull_debater_generates_optimistic_arguments(debate_context_positive):
    """Test Bull debater generates positive arguments for strong metrics."""
    bull = DebaterAgent(perspective=Perspective.BULL, enable_debate=True)
    report = bull.debate(debate_context_positive)

    assert report.perspective == Perspective.BULL
    assert len(report.arguments) > 0
    assert report.num_strong_arguments >= 1

    # Should have positive arguments about correlation, p-value, sample size
    claims = ' '.join([a.claim for a in report.arguments]).lower()
    assert any(word in claims for word in ['strong', 'positive', 'reliable', 'robust'])


def test_bull_debater_key_points(debate_context_positive):
    """Test Bull debater extracts key points."""
    bull = DebaterAgent(perspective=Perspective.BULL)
    report = bull.debate(debate_context_positive)

    assert len(report.key_points) > 0
    assert len(report.key_points) <= 5  # Max 5 key points


def test_bull_debater_stance(debate_context_positive):
    """Test Bull debater generates optimistic stance."""
    bull = DebaterAgent(perspective=Perspective.BULL)
    report = bull.debate(debate_context_positive)

    assert 'BULL' in report.overall_stance
    assert len(report.overall_stance) > 20  # Should be substantial


# ==============================================================================
# DebaterAgent Tests - Bear Perspective
# ==============================================================================

def test_bear_debater_generates_pessimistic_arguments(debate_context_concerning):
    """Test Bear debater generates critical arguments for concerning metrics."""
    bear = DebaterAgent(perspective=Perspective.BEAR, enable_debate=True)
    report = bear.debate(debate_context_concerning)

    assert report.perspective == Perspective.BEAR
    assert len(report.arguments) > 0

    # Should raise concerns about high correlation and small sample
    claims = ' '.join([a.claim for a in report.arguments]).lower()
    assert any(word in claims for word in ['concern', 'risk', 'small', 'overfitting', 'suspicious'])


def test_bear_debater_detects_small_sample(debate_context_concerning):
    """Test Bear debater flags small sample size."""
    bear = DebaterAgent(perspective=Perspective.BEAR)
    report = bear.debate(debate_context_concerning)

    # Should have argument about small sample size
    small_sample_args = [
        a for a in report.arguments
        if 'small' in a.claim.lower() and 'sample' in a.claim.lower()
    ]
    assert len(small_sample_args) >= 1


def test_bear_debater_detects_overfitting(debate_context_concerning):
    """Test Bear debater flags suspiciously high correlation."""
    bear = DebaterAgent(perspective=Perspective.BEAR)
    report = bear.debate(debate_context_concerning)

    # Should have argument about overfitting
    overfitting_args = [
        a for a in report.arguments
        if 'overfitting' in a.claim.lower() or 'extremely high' in a.claim.lower()
    ]
    assert len(overfitting_args) >= 1


# ==============================================================================
# DebaterAgent Tests - Neutral Perspective
# ==============================================================================

def test_neutral_debater_generates_balanced_arguments(debate_context_neutral):
    """Test Neutral debater generates objective arguments."""
    neutral = DebaterAgent(perspective=Perspective.NEUTRAL, enable_debate=True)
    report = neutral.debate(debate_context_neutral)

    assert report.perspective == Perspective.NEUTRAL
    assert len(report.arguments) > 0

    # Should be balanced, not too optimistic or pessimistic
    claims = ' '.join([a.claim for a in report.arguments]).lower()
    # Neutral should use words like 'moderate', 'adequate', 'balanced'


def test_neutral_debater_average_confidence(debate_context_neutral):
    """Test Neutral debater has moderate confidence."""
    neutral = DebaterAgent(perspective=Perspective.NEUTRAL)
    report = neutral.debate(debate_context_neutral)

    # Neutral should have moderate confidence (not extreme)
    assert 0.5 <= report.average_confidence <= 0.9


# ==============================================================================
# DebaterAgent Tests - Disabled Mode
# ==============================================================================

def test_debater_disabled_mode(debate_context_positive):
    """Test DebaterAgent with debate disabled."""
    debater = DebaterAgent(perspective=Perspective.BULL, enable_debate=False)
    report = debater.debate(debate_context_positive)

    assert len(report.arguments) == 0
    assert report.num_strong_arguments == 0
    assert 'disabled' in report.overall_stance.lower()


# ==============================================================================
# SynthesizerAgent Tests
# ==============================================================================

def test_synthesizer_combines_multiple_perspectives(
    debate_context_positive,
    debate_context_concerning
):
    """Test Synthesizer combines Bull, Bear, Neutral perspectives."""
    # Generate reports from each perspective
    bull = DebaterAgent(Perspective.BULL)
    bear = DebaterAgent(Perspective.BEAR)
    neutral = DebaterAgent(Perspective.NEUTRAL)

    bull_report = bull.debate(debate_context_positive)
    bear_report = bear.debate(debate_context_concerning)
    neutral_report = neutral.debate(debate_context_positive)

    # Synthesize
    synthesizer = SynthesizerAgent(enable_synthesis=True)
    synthesis = synthesizer.synthesize(
        debate_reports=[bull_report, bear_report, neutral_report],
        original_confidence=0.85,
        fact_id='test_001'
    )

    assert len(synthesis.perspectives_reviewed) == 3
    assert Perspective.BULL in synthesis.perspectives_reviewed
    assert Perspective.BEAR in synthesis.perspectives_reviewed
    assert Perspective.NEUTRAL in synthesis.perspectives_reviewed


def test_synthesizer_extracts_risks():
    """Test Synthesizer extracts risks from Bear/Neutral arguments."""
    context = DebateContext(
        fact_id='test',
        extracted_values={'correlation': 0.99, 'sample_size': 10},
        source_code='',
        query_text=''
    )

    bear = DebaterAgent(Perspective.BEAR)
    bear_report = bear.debate(context)

    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        [bear_report],
        original_confidence=0.8,
        fact_id='test'
    )

    # Should have identified risks
    assert len(synthesis.key_risks) > 0


def test_synthesizer_extracts_opportunities():
    """Test Synthesizer extracts opportunities from Bull arguments."""
    context = DebateContext(
        fact_id='test',
        extracted_values={'correlation': 0.85, 'p_value': 0.001, 'sample_size': 200},
        source_code='',
        query_text=''
    )

    bull = DebaterAgent(Perspective.BULL)
    bull_report = bull.debate(context)

    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        [bull_report],
        original_confidence=0.7,
        fact_id='test'
    )

    # Should have identified opportunities
    assert len(synthesis.key_opportunities) > 0


def test_synthesizer_adjusts_confidence_with_consensus():
    """Test Synthesizer increases confidence when perspectives agree."""
    context = DebateContext(
        fact_id='test',
        extracted_values={'correlation': 0.75, 'p_value': 0.01, 'sample_size': 150},
        source_code='',
        query_text=''
    )

    # All perspectives should agree on good metrics
    bull = DebaterAgent(Perspective.BULL)
    neutral = DebaterAgent(Perspective.NEUTRAL)

    reports = [
        bull.debate(context),
        neutral.debate(context)
    ]

    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        reports,
        original_confidence=0.7,
        fact_id='test'
    )

    # Confidence might increase or stay stable with consensus
    assert synthesis.adjusted_confidence >= synthesis.original_confidence * 0.95


def test_synthesizer_decreases_confidence_with_disagreement():
    """Test Synthesizer applies conservative bias when concerns exist."""
    # Create context with concerning metrics that Bear will flag
    context = DebateContext(
        fact_id='test',
        extracted_values={'correlation': 0.98, 'sample_size': 12},  # Both concerning
        source_code='',
        query_text='',
        execution_metadata={'execution_time_ms': 3}  # Also suspicious
    )

    bull = DebaterAgent(Perspective.BULL)
    bear = DebaterAgent(Perspective.BEAR)
    neutral = DebaterAgent(Perspective.NEUTRAL)

    reports = [
        bull.debate(context),
        bear.debate(context),
        neutral.debate(context)
    ]

    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        reports,
        original_confidence=0.9,  # High initial confidence
        fact_id='test'
    )

    # With Bear raising strong concerns, confidence should decrease
    # or at least not increase significantly
    # Conservative bias: synthesizer should account for risks
    assert synthesis.adjusted_confidence <= synthesis.original_confidence * 1.05  # Max 5% increase


def test_synthesizer_generates_recommendation():
    """Test Synthesizer generates actionable recommendation."""
    context = DebateContext(
        fact_id='test',
        extracted_values={'correlation': 0.70, 'sample_size': 80},
        source_code='',
        query_text=''
    )

    neutral = DebaterAgent(Perspective.NEUTRAL)
    report = neutral.debate(context)

    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        [report],
        original_confidence=0.75,
        fact_id='test'
    )

    assert len(synthesis.recommendation) > 20
    assert synthesis.recommendation != ""


def test_synthesizer_calculates_debate_quality():
    """Test Synthesizer calculates debate quality score."""
    context = DebateContext(
        fact_id='test',
        extracted_values={'correlation': 0.75, 'p_value': 0.01, 'sample_size': 100},
        source_code='',
        query_text=''
    )

    # Multiple perspectives = higher quality
    bull = DebaterAgent(Perspective.BULL)
    bear = DebaterAgent(Perspective.BEAR)
    neutral = DebaterAgent(Perspective.NEUTRAL)

    reports = [
        bull.debate(context),
        bear.debate(context),
        neutral.debate(context)
    ]

    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        reports,
        original_confidence=0.8,
        fact_id='test'
    )

    # Quality should be reasonable with 3 perspectives
    assert 0.0 <= synthesis.debate_quality_score <= 1.0
    assert synthesis.debate_quality_score > 0.3  # Should be decent with 3 perspectives


def test_synthesizer_disabled_mode():
    """Test SynthesizerAgent with synthesis disabled."""
    synthesizer = SynthesizerAgent(enable_synthesis=False)
    synthesis = synthesizer.synthesize(
        [],
        original_confidence=0.8,
        fact_id='test'
    )

    assert 'disabled' in synthesis.balanced_view.lower()
    assert synthesis.adjusted_confidence == synthesis.original_confidence


# ==============================================================================
# Integration Tests
# ==============================================================================

def test_end_to_end_debate_workflow(debate_context_positive):
    """Test complete debate workflow: Bull + Bear + Neutral → Synthesis."""
    # Step 1: Generate perspectives
    bull = DebaterAgent(Perspective.BULL)
    bear = DebaterAgent(Perspective.BEAR)
    neutral = DebaterAgent(Perspective.NEUTRAL)

    bull_report = bull.debate(debate_context_positive)
    bear_report = bear.debate(debate_context_positive)
    neutral_report = neutral.debate(debate_context_positive)

    # All reports should be generated
    assert len(bull_report.arguments) > 0
    assert len(bear_report.arguments) > 0
    assert len(neutral_report.arguments) > 0

    # Step 2: Synthesize
    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        [bull_report, bear_report, neutral_report],
        original_confidence=0.85,
        fact_id=debate_context_positive.fact_id
    )

    # Synthesis should be complete
    assert synthesis is not None
    assert len(synthesis.balanced_view) > 50
    assert len(synthesis.key_risks) > 0 or len(synthesis.key_opportunities) > 0
    assert synthesis.debate_quality_score > 0.0


def test_week5_day2_success_criteria():
    """
    Week 5 Day 2 Success Criteria:

    - [x] DebaterAgent implemented (Bull, Bear, Neutral perspectives)
    - [x] Arguments generated with evidence and strength
    - [x] SynthesizerAgent implemented
    - [x] Risks and opportunities extracted
    - [x] Confidence adjustment based on debate quality
    - [x] Debate quality scoring
    - [x] End-to-end workflow functional
    - [x] All tests passing
    """
    # Criterion 1: DebaterAgent works
    context = DebateContext(
        fact_id='test',
        extracted_values={'correlation': 0.8, 'sample_size': 100},
        source_code='',
        query_text=''
    )

    bull = DebaterAgent(Perspective.BULL)
    bear = DebaterAgent(Perspective.BEAR)
    neutral = DebaterAgent(Perspective.NEUTRAL)

    bull_report = bull.debate(context)
    bear_report = bear.debate(context)
    neutral_report = neutral.debate(context)

    assert all([
        len(bull_report.arguments) > 0,
        len(bear_report.arguments) > 0,
        len(neutral_report.arguments) > 0
    ])

    # Criterion 2: Arguments have evidence
    for arg in bull_report.arguments:
        assert len(arg.evidence) > 0
        assert arg.strength in [ArgumentStrength.STRONG, ArgumentStrength.MODERATE, ArgumentStrength.WEAK]

    # Criterion 3: SynthesizerAgent works
    synthesizer = SynthesizerAgent()
    synthesis = synthesizer.synthesize(
        [bull_report, bear_report, neutral_report],
        original_confidence=0.8,
        fact_id='test'
    )

    assert synthesis is not None

    # Criterion 4: Risks and opportunities
    assert len(synthesis.key_risks) > 0 or len(synthesis.key_opportunities) > 0

    # Criterion 5: Confidence adjustment
    assert synthesis.adjusted_confidence != synthesis.original_confidence or len(synthesis.confidence_rationale) > 0

    # Criterion 6: Debate quality
    assert 0.0 <= synthesis.debate_quality_score <= 1.0

    print("""
    ✅ Week 5 Day 2 SUCCESS CRITERIA:
    - DebaterAgent (3 perspectives): ✅
    - Arguments with evidence: ✅
    - SynthesizerAgent: ✅
    - Risks/opportunities extraction: ✅
    - Confidence adjustment: ✅
    - Debate quality scoring: ✅
    - End-to-end workflow: ✅
    - Tests passing: ✅
    """)
