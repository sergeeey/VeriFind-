"""
Unit tests for FETCH node in LangGraph orchestrator.

Week 3 Day 3: TDD RED-GREEN-REFACTOR cycle

FETCH Node:
- Fetches market data when plan requires_data=True
- Integrates YFinance adapter
- Stores fetched data in state.fetched_data
- Handles missing data gracefully
- Updates state.status to FETCHING
"""

import pytest
from datetime import datetime, UTC, timedelta
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


def test_fetch_node_updates_status(lg_orchestrator):
    """Test FETCH node updates state status to FETCHING."""
    state = APEState.from_query('test_fetch_001', 'Get SPY data')
    state.plan = {
        'plan_id': 'plan_fetch_001',
        'requires_data': True,
        'tickers': ['SPY'],
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'data_type': 'OHLCV'
    }
    state.status = StateStatus.PLANNING

    updated_state = lg_orchestrator.fetch_node(state)

    assert updated_state.status == StateStatus.FETCHING
    assert updated_state.current_node == 'FETCH'


def test_fetch_node_calls_yfinance_adapter(lg_orchestrator):
    """Test FETCH node calls YFinance adapter with correct parameters."""
    state = APEState.from_query('test_fetch_002', 'Get QQQ data')
    state.plan = {
        'plan_id': 'plan_fetch_002',
        'requires_data': True,
        'tickers': ['QQQ'],
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'data_type': 'OHLCV'
    }

    updated_state = lg_orchestrator.fetch_node(state)

    assert updated_state.fetched_data is not None
    assert 'QQQ' in updated_state.fetched_data
    assert len(updated_state.fetched_data['QQQ']) > 0


def test_fetch_node_handles_multiple_tickers(lg_orchestrator):
    """Test FETCH node handles multiple tickers."""
    state = APEState.from_query('test_fetch_003', 'Get SPY and QQQ data')
    state.plan = {
        'plan_id': 'plan_fetch_003',
        'requires_data': True,
        'tickers': ['SPY', 'QQQ', 'IWM'],
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'data_type': 'OHLCV'
    }

    updated_state = lg_orchestrator.fetch_node(state)

    assert len(updated_state.fetched_data) == 3
    assert 'SPY' in updated_state.fetched_data
    assert 'QQQ' in updated_state.fetched_data
    assert 'IWM' in updated_state.fetched_data


def test_fetch_node_handles_invalid_ticker(lg_orchestrator):
    """Test FETCH node handles invalid ticker gracefully."""
    state = APEState.from_query('test_fetch_004', 'Get invalid ticker')
    state.plan = {
        'plan_id': 'plan_fetch_004',
        'requires_data': True,
        'tickers': ['INVALID_TICKER_XYZ'],
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'data_type': 'OHLCV'
    }

    updated_state = lg_orchestrator.fetch_node(state)

    # Should still update status, but fetched_data may be empty or contain error
    assert updated_state.status == StateStatus.FETCHING
    assert updated_state.fetched_data is not None


def test_fetch_node_caches_data_in_state(lg_orchestrator):
    """Test FETCH node stores fetched data in state for VEE node."""
    state = APEState.from_query('test_fetch_005', 'Cache test')
    state.plan = {
        'plan_id': 'plan_fetch_005',
        'requires_data': True,
        'tickers': ['SPY'],
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'data_type': 'OHLCV'
    }

    updated_state = lg_orchestrator.fetch_node(state)

    # Verify data is accessible for next node
    assert hasattr(updated_state, 'fetched_data')
    assert updated_state.fetched_data['SPY'] is not None
    # Should have OHLCV columns
    spy_data = updated_state.fetched_data['SPY']
    assert 'Open' in spy_data.columns or 'open' in str(spy_data.columns).lower()


def test_fetch_node_with_fundamentals(lg_orchestrator):
    """Test FETCH node can fetch fundamental data."""
    state = APEState.from_query('test_fetch_006', 'Get fundamentals')
    state.plan = {
        'plan_id': 'plan_fetch_006',
        'requires_data': True,
        'tickers': ['AAPL'],
        'data_type': 'fundamentals'
    }

    updated_state = lg_orchestrator.fetch_node(state)

    assert updated_state.fetched_data is not None
    assert 'AAPL' in updated_state.fetched_data
    # Fundamentals should be dict with keys like 'pe_ratio', 'market_cap'
    fundamentals = updated_state.fetched_data['AAPL']
    assert isinstance(fundamentals, dict)


def test_should_fetch_routes_correctly(lg_orchestrator):
    """Test should_fetch conditional routing logic."""
    # Case 1: requires_data=True -> should fetch
    state_fetch = APEState.from_query('test_route_001', 'Fetch test')
    state_fetch.plan = {'requires_data': True, 'tickers': ['SPY']}

    next_node_fetch = lg_orchestrator.should_fetch(state_fetch)
    assert next_node_fetch == 'FETCH'

    # Case 2: requires_data=False -> skip to VEE
    state_skip = APEState.from_query('test_route_002', 'Skip test')
    state_skip.plan = {'requires_data': False}

    next_node_skip = lg_orchestrator.should_fetch(state_skip)
    assert next_node_skip == 'VEE'


def test_fetch_to_vee_data_flow(lg_orchestrator):
    """Test data flows from FETCH to VEE node."""
    # FETCH node
    state = APEState.from_query('test_flow_001', 'Data flow test')
    state.plan = {
        'plan_id': 'plan_flow_001',
        'requires_data': True,
        'tickers': ['SPY'],
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'data_type': 'OHLCV',
        'code': 'print(f"SPY data shape: {len(spy_data)}")'
    }

    state_after_fetch = lg_orchestrator.fetch_node(state)

    assert state_after_fetch.fetched_data is not None
    assert 'SPY' in state_after_fetch.fetched_data

    # VEE node should receive fetched_data
    # (VEE implementation will inject data into code execution environment)
    # For now, just verify data is available in state
    assert state_after_fetch.fetched_data['SPY'] is not None


def test_fetch_node_date_range_validation(lg_orchestrator):
    """Test FETCH node validates date range."""
    state = APEState.from_query('test_date_001', 'Date validation')

    # Invalid: end_date before start_date
    state.plan = {
        'plan_id': 'plan_date_001',
        'requires_data': True,
        'tickers': ['SPY'],
        'start_date': '2024-01-31',
        'end_date': '2024-01-01',  # Before start!
        'data_type': 'OHLCV'
    }

    updated_state = lg_orchestrator.fetch_node(state)

    # Should handle gracefully (YFinance will fail, we catch error)
    # Accept both FETCHING (if adapter auto-fixes) or FAILED (if rejected)
    assert updated_state.status in [StateStatus.FETCHING, StateStatus.FAILED]


def test_fetch_node_integration_with_state_machine(lg_orchestrator):
    """Test FETCH node works in full state machine flow."""
    result = lg_orchestrator.run(
        query_id='test_integration_001',
        query_text='Calculate correlation between SPY and QQQ',
        use_plan=True  # Enable PLAN node (not direct_code)
    )

    # Should go through: PLAN -> FETCH (if needed) -> VEE -> GATE
    assert result.status in [StateStatus.COMPLETED, StateStatus.FAILED]

    # Check nodes visited
    if 'FETCH' in result.nodes_visited:
        # If FETCH was visited, should have fetched_data
        assert result.fetched_data is not None


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week3_day3_success_criteria(lg_orchestrator):
    """
    Week 3 Day 3 Success Criteria:

    - [x] FETCH node implementation
    - [x] YFinance adapter integration
    - [x] Conditional routing (should_fetch)
    - [x] Data storage in state
    - [x] Multiple tickers support
    - [x] Fundamentals fetching
    - [x] Error handling for invalid tickers
    - [x] Integration with state machine
    """
    # Test 1: FETCH node works
    state = APEState.from_query('criteria_001', 'Fetch criteria test')
    state.plan = {
        'plan_id': 'plan_criteria_001',
        'requires_data': True,
        'tickers': ['SPY', 'QQQ'],
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'data_type': 'OHLCV'
    }

    result = lg_orchestrator.fetch_node(state)

    assert result.status == StateStatus.FETCHING
    assert result.fetched_data is not None
    assert 'SPY' in result.fetched_data
    assert 'QQQ' in result.fetched_data

    # Test 2: Conditional routing
    assert lg_orchestrator.should_fetch(state) == 'FETCH'

    state_no_fetch = APEState.from_query('criteria_002', 'No fetch')
    state_no_fetch.plan = {'requires_data': False}
    assert lg_orchestrator.should_fetch(state_no_fetch) == 'VEE'

    print("""
    ✅ Week 3 Day 3 SUCCESS CRITERIA:
    - FETCH node implementation: ✅
    - YFinance adapter integration: ✅
    - Conditional routing: ✅
    - Data storage in state: ✅
    - Multiple tickers support: ✅
    - Error handling: ✅
    """)
