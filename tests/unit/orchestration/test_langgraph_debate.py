"""
Unit tests for LangGraph Debate Integration.

Week 5 Day 3: Integration tests for DEBATE node in state machine.

Tests cover:
- debate_node() execution
- State flow: GATE → DEBATE → END
- Confidence adjustment via Debate System
- Error handling
"""

import pytest
from unittest.mock import Mock, patch

from src.orchestration.langgraph_orchestrator import (
    LangGraphOrchestrator,
    APEState,
    StateStatus
)
from src.truth_boundary.gate import VerifiedFact
from src.debate.schemas import Perspective, DebateReport, Synthesis


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def orchestrator():
    """Create orchestrator for debate testing."""
    return LangGraphOrchestrator(
        claude_api_key='test_api_key',
        enable_retry=False,
        use_real_llm=False
    )


@pytest.fixture
def state_after_gate():
    """State after GATE node with VerifiedFact."""
    from datetime import datetime, UTC

    verified_fact = VerifiedFact(
        fact_id='test_fact_001',
        query_id='query_001',
        plan_id='plan_001',
        code_hash='abc123',
        status='success',
        extracted_values={
            'correlation': 0.75,
            'p_value': 0.01,
            'sample_size': 150
        },
        execution_time_ms=1500,
        memory_used_mb=50.0,
        created_at=datetime.now(UTC),
        error_message=None,
        source_code='# Analysis code',
        confidence_score=0.85
    )

    return APEState(
        query_id='query_001',
        query_text='Calculate correlation between SPY and QQQ',
        status=StateStatus.VALIDATING,
        verified_fact=verified_fact
    )


@pytest.fixture
def state_without_verified_fact():
    """State without VerifiedFact (should fail)."""
    return APEState(
        query_id='query_002',
        query_text='Test query',
        status=StateStatus.VALIDATING,
        verified_fact=None
    )


# ==============================================================================
# debate_node() Tests
# ==============================================================================

def test_debate_node_success(orchestrator, state_after_gate):
    """Test debate_node executes successfully with VerifiedFact."""
    result = orchestrator.debate_node(state_after_gate)

    assert result.status == StateStatus.COMPLETED
    assert result.current_node == 'DEBATE'
    assert 'DEBATE' in result.nodes_visited

    # Debate reports generated
    assert result.debate_reports is not None
    assert len(result.debate_reports) == 3  # Bull, Bear, Neutral

    # Verify perspectives
    perspectives = [r.perspective for r in result.debate_reports]
    assert Perspective.BULL in perspectives
    assert Perspective.BEAR in perspectives
    assert Perspective.NEUTRAL in perspectives

    # Synthesis generated
    assert result.synthesis is not None
    assert isinstance(result.synthesis, Synthesis)
    assert result.synthesis.fact_id == 'test_fact_001'

    # Confidence adjusted
    assert result.verified_fact.confidence_score == result.synthesis.adjusted_confidence


def test_debate_node_adjusts_confidence(orchestrator, state_after_gate):
    """Test debate_node adjusts VerifiedFact confidence."""
    original_confidence = state_after_gate.verified_fact.confidence_score
    result = orchestrator.debate_node(state_after_gate)

    assert result.status == StateStatus.COMPLETED
    assert result.synthesis is not None

    # Confidence may increase, decrease, or stay same
    adjusted_confidence = result.synthesis.adjusted_confidence
    assert 0.0 <= adjusted_confidence <= 1.0

    # VerifiedFact updated
    assert result.verified_fact.confidence_score == adjusted_confidence

    # Rationale provided
    assert len(result.synthesis.confidence_rationale) > 0


def test_debate_node_extracts_risks_and_opportunities(orchestrator, state_after_gate):
    """Test debate_node extracts risks and opportunities."""
    result = orchestrator.debate_node(state_after_gate)

    assert result.status == StateStatus.COMPLETED
    assert result.synthesis is not None

    # Should have risks or opportunities (or both)
    has_insights = (
        len(result.synthesis.key_risks) > 0 or
        len(result.synthesis.key_opportunities) > 0
    )
    assert has_insights


def test_debate_node_generates_balanced_view(orchestrator, state_after_gate):
    """Test debate_node generates balanced synthesis."""
    result = orchestrator.debate_node(state_after_gate)

    assert result.status == StateStatus.COMPLETED
    assert result.synthesis is not None

    # Balanced view should be substantial
    assert len(result.synthesis.balanced_view) > 50

    # Should mention multiple perspectives
    balanced_view = result.synthesis.balanced_view.lower()
    assert any(p in balanced_view for p in ['bull', 'bear', 'neutral', 'perspective'])


def test_debate_node_without_verified_fact(orchestrator, state_without_verified_fact):
    """Test debate_node fails gracefully without VerifiedFact."""
    result = orchestrator.debate_node(state_without_verified_fact)

    assert result.status == StateStatus.FAILED
    assert result.error_message == 'No verified fact to debate'
    assert result.current_node == 'DEBATE'


def test_debate_node_context_creation(orchestrator, state_after_gate):
    """Test debate_node creates proper DebateContext."""
    result = orchestrator.debate_node(state_after_gate)

    assert result.status == StateStatus.COMPLETED

    # Verify debate reports have correct fact_id
    for report in result.debate_reports:
        assert report.fact_id == 'test_fact_001'


# ==============================================================================
# State Flow Integration Tests
# ==============================================================================

def test_state_flow_includes_debate(orchestrator):
    """Test get_next_node routing includes DEBATE after VALIDATING."""
    # VALIDATING → DEBATE
    next_node = orchestrator.get_next_node(StateStatus.VALIDATING)
    assert next_node == 'DEBATE'

    # DEBATING → END
    next_node = orchestrator.get_next_node(StateStatus.DEBATING)
    assert next_node == 'END'


def test_state_status_enum_includes_debating():
    """Test StateStatus enum has DEBATING value."""
    assert hasattr(StateStatus, 'DEBATING')
    assert StateStatus.DEBATING.value == 'debating'


def test_ape_state_has_debate_fields():
    """Test APEState dataclass has debate-related fields."""
    state = APEState(
        query_id='test',
        query_text='test query'
    )

    assert hasattr(state, 'debate_reports')
    assert hasattr(state, 'synthesis')
    assert state.debate_reports is None  # Default
    assert state.synthesis is None


# ==============================================================================
# Error Handling Tests
# ==============================================================================

def test_debate_node_handles_exceptions(orchestrator, state_after_gate):
    """Test debate_node handles exceptions gracefully."""
    # Mock DebaterAgent to raise exception
    with patch('src.orchestration.langgraph_orchestrator.DebaterAgent') as mock_agent:
        mock_agent.return_value.debate.side_effect = Exception('Mock debate error')

        result = orchestrator.debate_node(state_after_gate)

        assert result.status == StateStatus.FAILED
        assert 'Debate failed' in result.error_message
        assert 'Mock debate error' in result.error_message


# ==============================================================================
# Week 5 Day 3 Success Criteria Test
# ==============================================================================

def test_week5_day3_success_criteria(orchestrator, state_after_gate):
    """
    Week 5 Day 3 Success Criteria:

    - [x] debate_node() implemented in LangGraphOrchestrator
    - [x] APEState extended with debate_reports and synthesis
    - [x] StateStatus.DEBATING added
    - [x] State flow routing includes DEBATE (VALIDATING → DEBATE → END)
    - [x] DebateContext created from VerifiedFact
    - [x] Bull/Bear/Neutral perspectives generated
    - [x] Synthesis combines perspectives
    - [x] Confidence adjusted in VerifiedFact
    - [x] Integration tests passing
    """
    # Criterion 1: debate_node exists and works
    result = orchestrator.debate_node(state_after_gate)
    assert result.status == StateStatus.COMPLETED

    # Criterion 2: APEState fields exist
    assert hasattr(result, 'debate_reports')
    assert hasattr(result, 'synthesis')

    # Criterion 3: StateStatus.DEBATING exists
    assert StateStatus.DEBATING in StateStatus

    # Criterion 4: Routing includes DEBATE
    assert orchestrator.get_next_node(StateStatus.VALIDATING) == 'DEBATE'
    assert orchestrator.get_next_node(StateStatus.DEBATING) == 'END'

    # Criterion 5: DebateContext created (implicit via successful debate)
    assert result.debate_reports is not None

    # Criterion 6: 3 perspectives generated
    assert len(result.debate_reports) == 3
    perspectives = [r.perspective for r in result.debate_reports]
    assert set(perspectives) == {Perspective.BULL, Perspective.BEAR, Perspective.NEUTRAL}

    # Criterion 7: Synthesis exists
    assert result.synthesis is not None
    assert isinstance(result.synthesis, Synthesis)

    # Criterion 8: Confidence adjusted
    assert result.verified_fact.confidence_score == result.synthesis.adjusted_confidence

    print("""
    ✅ Week 5 Day 3 SUCCESS CRITERIA:
    - debate_node() implemented: ✅
    - APEState extended: ✅
    - StateStatus.DEBATING added: ✅
    - State flow routing updated: ✅
    - DebateContext from VerifiedFact: ✅
    - 3 perspectives generated: ✅
    - Synthesis combines perspectives: ✅
    - Confidence adjusted: ✅
    - Integration tests passing: ✅
    """)
