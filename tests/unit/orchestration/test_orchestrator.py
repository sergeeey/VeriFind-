"""
Unit tests for APE Orchestrator.

Week 2 Day 5: Simple orchestrator testing.
"""

import pytest

# Skip this module: APEOrchestrator is legacy (Week 2)
# Production uses ParallelDebateOrchestrator (see eval/run_golden_set_v2.py)
pytest.skip("APEOrchestrator is legacy, not used in production", allow_module_level=True)

from src.orchestration.orchestrator import APEOrchestrator, QueryResult


@pytest.fixture
def orchestrator():
    """Create orchestrator for testing."""
    return APEOrchestrator(
        claude_api_key='mock_key',
        vee_config={
            'memory_limit': '128m',
            'cpu_limit': 0.25,
            'timeout': 10
        }
    )


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes all components."""
    assert orchestrator is not None
    assert orchestrator.plan_node is not None
    assert orchestrator.vee_sandbox is not None
    assert orchestrator.truth_gate is not None


def test_orchestrator_stats(orchestrator):
    """Test getting orchestrator statistics."""
    stats = orchestrator.get_stats()

    assert stats['plan_node_initialized'] is True
    assert stats['vee_sandbox_initialized'] is True
    assert stats['truth_gate_initialized'] is True
    assert stats['vee_memory_limit'] == '128m'
    assert stats['vee_timeout'] == 10


def test_process_query_with_direct_code(orchestrator):
    """Test processing query with direct code (skip PLAN)."""
    query_id = 'test_001'
    query_text = 'Calculate correlation'
    direct_code = 'print("correlation: 0.95")'

    result = orchestrator.process_query(
        query_id=query_id,
        query_text=query_text,
        skip_plan=True,
        direct_code=direct_code
    )

    assert isinstance(result, QueryResult)
    assert result.query_id == query_id
    assert result.status == 'success'
    assert result.verified_fact is not None
    assert result.verified_fact.query_id == query_id
    assert result.verified_fact.extracted_values['correlation'] == 0.95


def test_process_query_execution_success(orchestrator):
    """Test successful query execution flow."""
    result = orchestrator.process_query(
        query_id='test_002',
        query_text='Test query',
        skip_plan=True,
        direct_code='import json; print(json.dumps({"value": 42}))'
    )

    assert result.status == 'success'
    assert result.plan_generated is True
    assert result.code_executed is True
    assert result.output_validated is True
    assert result.verified_fact.extracted_values['value'] == 42


def test_process_query_execution_error(orchestrator):
    """Test query with execution error."""
    result = orchestrator.process_query(
        query_id='test_003',
        query_text='Error test',
        skip_plan=True,
        direct_code='1/0'  # ZeroDivisionError
    )

    assert result.status == 'execution_error'
    assert result.code_executed is True
    assert 'ZeroDivisionError' in result.error_message
    assert result.verified_fact is None


def test_process_query_timeout(orchestrator):
    """Test query timeout handling."""
    result = orchestrator.process_query(
        query_id='test_004',
        query_text='Timeout test',
        skip_plan=True,
        direct_code='import time; time.sleep(60)'
    )

    assert result.status == 'execution_error'
    assert result.verified_fact is None


def test_process_batch_queries(orchestrator):
    """Test batch query processing."""
    queries = [
        ('batch_001', 'Query 1'),
        ('batch_002', 'Query 2'),
        ('batch_003', 'Query 3')
    ]

    direct_codes = [
        'print("value: 10")',
        'print("value: 20")',
        'print("value: 30")'
    ]

    results = orchestrator.process_batch(queries, direct_codes)

    assert len(results) == 3
    assert all(r.status == 'success' for r in results)
    assert results[0].verified_fact.extracted_values['value'] == 10
    assert results[1].verified_fact.extracted_values['value'] == 20
    assert results[2].verified_fact.extracted_values['value'] == 30


def test_process_batch_with_errors(orchestrator):
    """Test batch processing with mixed success/error."""
    queries = [
        ('batch_004', 'Success'),
        ('batch_005', 'Error'),
        ('batch_006', 'Success')
    ]

    direct_codes = [
        'print("value: 1")',
        '1/0',  # Error
        'print("value: 2")'
    ]

    results = orchestrator.process_batch(queries, direct_codes)

    assert len(results) == 3
    assert results[0].status == 'success'
    assert results[1].status == 'execution_error'
    assert results[2].status == 'success'


def test_query_result_dataclass():
    """Test QueryResult dataclass structure."""
    result = QueryResult(
        query_id='test',
        query_text='Test query',
        status='success',
        plan_generated=True,
        code_executed=True,
        output_validated=True
    )

    assert result.query_id == 'test'
    assert result.status == 'success'
    assert result.plan_generated is True


def test_orchestrator_logging(orchestrator, caplog):
    """Test orchestrator logging output."""
    import logging
    caplog.set_level(logging.INFO)

    orchestrator.process_query(
        query_id='log_test',
        query_text='Logging test',
        skip_plan=True,
        direct_code='print("test")'
    )

    # Check that logs were generated
    assert 'Processing query' in caplog.text
    assert 'VEE: Executing' in caplog.text
    assert 'GATE: Validating' in caplog.text


def test_orchestrator_without_skip_plan(orchestrator):
    """Test orchestrator without skip_plan (should fail without real API)."""
    result = orchestrator.process_query(
        query_id='plan_test',
        query_text='This needs real PLAN node'
    )

    # Should fail because PLAN node needs real Claude API
    assert result.status == 'plan_error'
    assert 'PLAN node requires Claude API' in result.error_message
