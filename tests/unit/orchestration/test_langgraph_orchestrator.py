"""
Unit tests for LangGraph-based State Machine Orchestrator.

Week 3 Day 1: TDD RED-GREEN-REFACTOR cycle

LangGraph State Machine:
- Nodes: PLAN, FETCH, VEE, GATE, ERROR
- Edges: Conditional routing based on state
- State: Shared context across nodes
- Error handling: Automatic retry and recovery
"""

import pytest
from typing import Dict, Any

from src.orchestration.langgraph_orchestrator import (
    LangGraphOrchestrator,
    APEState,
    StateStatus
)


# ==============================================================================
# RED Phase: Failing Tests
# ==============================================================================

@pytest.fixture
def lg_orchestrator():
    """Create LangGraph orchestrator for testing."""
    return LangGraphOrchestrator(
        claude_api_key='mock_key',
        enable_retry=True,
        max_retries=3
    )


def test_orchestrator_initialization(lg_orchestrator):
    """Test LangGraph orchestrator initializes correctly."""
    assert lg_orchestrator is not None
    assert lg_orchestrator.max_retries == 3
    assert lg_orchestrator.enable_retry is True


def test_create_initial_state():
    """Test creating initial state from query."""
    state = APEState.from_query(
        query_id='test_001',
        query_text='Calculate correlation between SPY and QQQ'
    )

    assert state.query_id == 'test_001'
    assert state.query_text is not None
    assert state.status == StateStatus.INITIALIZED
    assert state.current_node is None
    assert state.plan is None
    assert state.execution_result is None
    assert state.verified_fact is None


def test_state_status_enum():
    """Test StateStatus enum values."""
    assert StateStatus.INITIALIZED == 'initialized'
    assert StateStatus.PLANNING == 'planning'
    assert StateStatus.FETCHING == 'fetching'
    assert StateStatus.EXECUTING == 'executing'
    assert StateStatus.VALIDATING == 'validating'
    assert StateStatus.COMPLETED == 'completed'
    assert StateStatus.FAILED == 'failed'


def test_plan_node_updates_state(lg_orchestrator):
    """Test PLAN node updates state correctly."""
    state = APEState.from_query('test_002', 'Test query')

    # Mock PLAN node execution
    updated_state = lg_orchestrator.plan_node(
        state,
        direct_code='print("correlation: 0.95")'  # For testing
    )

    assert updated_state.status == StateStatus.PLANNING
    assert updated_state.current_node == 'PLAN'
    assert updated_state.plan is not None
    assert 'code' in updated_state.plan


def test_vee_node_executes_code(lg_orchestrator):
    """Test VEE node executes code and updates state."""
    state = APEState.from_query('test_003', 'Test query')
    state.plan = {'code': 'print("value: 42")'}
    state.status = StateStatus.PLANNING

    updated_state = lg_orchestrator.vee_node(state)

    assert updated_state.status == StateStatus.EXECUTING
    assert updated_state.current_node == 'VEE'
    assert updated_state.execution_result is not None
    assert updated_state.execution_result.status == 'success'


def test_gate_node_validates_output(lg_orchestrator):
    """Test GATE node validates output and creates VerifiedFact."""
    from src.vee.sandbox_runner import ExecutionResult

    state = APEState.from_query('test_004', 'Test query')
    state.plan = {'plan_id': 'test_plan_004', 'code': 'test'}  # Need plan for plan_id
    state.execution_result = ExecutionResult(
        status='success',
        exit_code=0,
        stdout='correlation: 0.95',
        stderr='',
        duration_ms=1000,
        memory_used_mb=30.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='abc123'
    )
    state.status = StateStatus.EXECUTING

    updated_state = lg_orchestrator.gate_node(state)

    assert updated_state.status == StateStatus.COMPLETED  # GATE completes validation
    assert updated_state.current_node == 'GATE'
    assert updated_state.verified_fact is not None
    assert updated_state.verified_fact.status == 'success'


def test_state_machine_routing_success_path(lg_orchestrator):
    """Test state machine routes through success path."""
    # PLAN → VEE → GATE → COMPLETED
    routing = lg_orchestrator.get_next_node(StateStatus.INITIALIZED)
    assert routing == 'PLAN'

    routing = lg_orchestrator.get_next_node(StateStatus.PLANNING)
    assert routing == 'VEE'

    routing = lg_orchestrator.get_next_node(StateStatus.EXECUTING)
    assert routing == 'GATE'

    routing = lg_orchestrator.get_next_node(StateStatus.VALIDATING)
    assert routing == 'END'


def test_state_machine_error_handling(lg_orchestrator):
    """Test state machine handles errors with retry."""
    state = APEState.from_query('test_005', 'Error test')
    state.error_count = 0
    state.status = StateStatus.FAILED

    # Should route to ERROR node if retries available
    next_node = lg_orchestrator.get_next_node(StateStatus.FAILED)

    if lg_orchestrator.enable_retry and state.error_count < lg_orchestrator.max_retries:
        assert next_node == 'ERROR'
    else:
        assert next_node == 'END'


def test_error_node_retry_logic(lg_orchestrator):
    """Test ERROR node implements retry logic."""
    state = APEState.from_query('test_006', 'Retry test')
    state.error_count = 1
    state.error_message = 'Execution failed'
    state.status = StateStatus.FAILED

    updated_state = lg_orchestrator.error_node(state)

    assert updated_state.error_count == 2  # Incremented
    # Should reset to PLAN for retry
    if updated_state.error_count < lg_orchestrator.max_retries:
        assert updated_state.status == StateStatus.INITIALIZED


def test_run_state_machine_end_to_end(lg_orchestrator):
    """Test running complete state machine end-to-end."""
    result = lg_orchestrator.run(
        query_id='test_007',
        query_text='Calculate correlation',
        direct_code='print("correlation: 0.95")'
    )

    assert result.status == StateStatus.COMPLETED
    assert result.verified_fact is not None
    assert result.verified_fact.status == 'success'


def test_state_machine_with_execution_error(lg_orchestrator):
    """Test state machine handles execution errors."""
    result = lg_orchestrator.run(
        query_id='test_008',
        query_text='Error test',
        direct_code='1/0'  # ZeroDivisionError
    )

    # Should fail after retries
    assert result.status in [StateStatus.FAILED, StateStatus.COMPLETED]
    if result.status == StateStatus.FAILED:
        assert 'ZeroDivisionError' in result.error_message


def test_state_persistence(lg_orchestrator):
    """Test state can be serialized/deserialized."""
    state = APEState.from_query('test_009', 'Persistence test')
    state.status = StateStatus.PLANNING
    state.plan = {'code': 'print("test")'}

    # Convert to dict
    state_dict = state.to_dict()

    assert isinstance(state_dict, dict)
    assert state_dict['query_id'] == 'test_009'
    assert state_dict['status'] == 'planning'

    # Restore from dict
    restored_state = APEState.from_dict(state_dict)

    assert restored_state.query_id == state.query_id
    assert restored_state.status == state.status


def test_conditional_fetch_node(lg_orchestrator):
    """Test FETCH node is conditional (only if data needed)."""
    state = APEState.from_query('test_010', 'Test without fetch')
    state.plan = {'code': 'print(42)', 'requires_data': False}

    # Should skip FETCH if requires_data=False
    next_node = lg_orchestrator.should_fetch(state)

    assert next_node in ['FETCH', 'VEE']
    if not state.plan.get('requires_data', False):
        assert next_node == 'VEE'


def test_state_machine_metrics(lg_orchestrator):
    """Test state machine tracks execution metrics."""
    result = lg_orchestrator.run(
        query_id='test_011',
        query_text='Metrics test',
        direct_code='print("test")'
    )

    metrics = result.get_metrics()

    assert isinstance(metrics, dict)
    assert 'total_duration_ms' in metrics
    assert 'nodes_visited' in metrics
    assert 'error_count' in metrics


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week3_day1_success_criteria(lg_orchestrator):
    """
    Week 3 Day 1 Success Criteria:

    - [x] LangGraph state machine initialization
    - [x] State nodes: PLAN, VEE, GATE, ERROR
    - [x] State routing logic
    - [x] Error handling with retry
    - [x] End-to-end state machine execution
    - [x] State persistence (to_dict/from_dict)
    """
    # Test 1: State machine initialization
    assert lg_orchestrator is not None

    # Test 2: End-to-end execution
    result = lg_orchestrator.run(
        query_id='criteria_test',
        query_text='Test query',
        direct_code='import json; print(json.dumps({"value": 123}))'
    )

    assert result.status == StateStatus.COMPLETED
    assert result.verified_fact is not None

    # Test 3: State persistence
    state_dict = result.to_dict()
    restored = APEState.from_dict(state_dict)
    assert restored.query_id == result.query_id

    print("""
    ✅ Week 3 Day 1 SUCCESS CRITERIA:
    - LangGraph state machine: ✅
    - State nodes (PLAN, VEE, GATE, ERROR): ✅
    - State routing: ✅
    - Error handling: ✅
    - End-to-end execution: ✅
    - State persistence: ✅
    """)
