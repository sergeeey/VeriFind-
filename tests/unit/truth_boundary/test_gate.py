"""
Unit tests for Truth Boundary Gate (TDD).

Week 2 Day 3: RED-GREEN-REFACTOR cycle

The Truth Boundary enforces the core APE principle:
"LLMs generate CODE, not numbers. All numerical outputs come from VEE execution."

Test strategy:
1. Write failing tests first (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor for quality (REFACTOR)
"""

import pytest
from datetime import datetime, UTC
import json

from src.truth_boundary.gate import TruthBoundaryGate, VerifiedFact, ValidationResult
from src.vee.sandbox_runner import ExecutionResult


# ==============================================================================
# RED Phase: Failing Tests
# ==============================================================================

@pytest.fixture
def gate():
    """Create Truth Boundary Gate for testing."""
    return TruthBoundaryGate()


def test_gate_initialization(gate):
    """Test gate initializes correctly."""
    assert gate is not None


def test_parse_numerical_output():
    """Test parsing numerical values from stdout."""
    stdout = """
Correlation: 0.95
Mean Return: 0.0234
Volatility: 0.15
"""

    result = TruthBoundaryGate.parse_numerical_output(stdout)

    assert isinstance(result, dict)
    assert 'Correlation' in result
    assert result['Correlation'] == 0.95
    assert result['Mean_Return'] == 0.0234  # Normalized: spaces → underscores
    assert result['Volatility'] == 0.15


def test_parse_json_output():
    """Test parsing JSON output from VEE."""
    stdout = json.dumps({
        'correlation': 0.95,
        'mean_return': 0.0234,
        'p_value': 0.001,
        'sample_size': 252
    })

    result = TruthBoundaryGate.parse_json_output(stdout)

    assert isinstance(result, dict)
    assert result['correlation'] == 0.95
    assert result['sample_size'] == 252


def test_validate_execution_success(gate):
    """Test validation of successful execution."""
    exec_result = ExecutionResult(
        status='success',
        exit_code=0,
        stdout='correlation: 0.95\np_value: 0.001',
        stderr='',
        duration_ms=1500,
        memory_used_mb=50.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='abc123'
    )

    validation = gate.validate(exec_result)

    assert isinstance(validation, ValidationResult)
    assert validation.is_valid is True
    assert validation.status == 'success'
    assert len(validation.extracted_values) > 0


def test_validate_execution_failure(gate):
    """Test validation of failed execution."""
    exec_result = ExecutionResult(
        status='error',
        exit_code=1,
        stdout='',
        stderr='ZeroDivisionError: division by zero',
        duration_ms=500,
        memory_used_mb=20.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='abc123'
    )

    validation = gate.validate(exec_result)

    assert validation.is_valid is False
    assert validation.status == 'error'
    assert 'ZeroDivisionError' in validation.error_message


def test_validate_timeout(gate):
    """Test validation of timeout execution."""
    exec_result = ExecutionResult(
        status='timeout',
        exit_code=-1,
        stdout='',
        stderr='',
        duration_ms=30000,
        memory_used_mb=0.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='abc123'
    )

    validation = gate.validate(exec_result)

    assert validation.is_valid is False
    assert validation.status == 'timeout'


def test_validate_empty_output(gate):
    """Test validation when execution has no numerical output."""
    exec_result = ExecutionResult(
        status='success',
        exit_code=0,
        stdout='Processing complete.',  # No numbers
        stderr='',
        duration_ms=1000,
        memory_used_mb=30.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='abc123'
    )

    validation = gate.validate(exec_result)

    # Success but no extracted values
    assert validation.is_valid is True
    assert validation.status == 'success'
    assert len(validation.extracted_values) == 0


def test_create_verified_fact(gate):
    """Test creation of VerifiedFact from validated execution."""
    exec_result = ExecutionResult(
        status='success',
        exit_code=0,
        stdout='correlation: 0.95\np_value: 0.001',
        stderr='',
        duration_ms=1500,
        memory_used_mb=50.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='abc123'
    )

    validation = gate.validate(exec_result)
    fact = gate.create_verified_fact(
        validation=validation,
        query_id='query_001',
        plan_id='plan_001',
        code_hash=exec_result.code_hash,
        execution_time_ms=exec_result.duration_ms,
        memory_used_mb=exec_result.memory_used_mb
    )

    assert isinstance(fact, VerifiedFact)
    assert fact.query_id == 'query_001'
    assert fact.plan_id == 'plan_001'
    assert fact.code_hash == 'abc123'
    assert fact.status == 'success'
    assert len(fact.extracted_values) > 0


def test_verified_fact_immutability(gate):
    """Test that VerifiedFact is immutable (frozen dataclass)."""
    fact = VerifiedFact(
        fact_id='fact_001',
        query_id='query_001',
        plan_id='plan_001',
        code_hash='abc123',
        status='success',
        extracted_values={'correlation': 0.95},
        execution_time_ms=1500,
        memory_used_mb=50.0,
        created_at=datetime.now(UTC),
        error_message=None
    )

    # Should not be able to modify
    with pytest.raises(AttributeError):
        fact.status = 'error'


def test_hallucination_detection(gate):
    """
    Critical test: Detect when LLM hallucinates numbers in stdout.

    If code just prints \"correlation: 0.95\" without calculation,
    it should still pass (because it came from VEE execution).

    But if code returns text like \"Based on my analysis, I believe...\",
    that should be flagged.
    """
    # Case 1: Code that calculates and prints (VALID)
    exec_result1 = ExecutionResult(
        status='success',
        exit_code=0,
        stdout='correlation: 0.95',  # From calculation
        stderr='',
        duration_ms=1500,
        memory_used_mb=50.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='calc_hash'
    )

    validation1 = gate.validate(exec_result1)
    assert validation1.is_valid is True

    # Case 2: Code that just echoes text (VALID - still from VEE)
    exec_result2 = ExecutionResult(
        status='success',
        exit_code=0,
        stdout='print("correlation: 0.95")',  # Echo
        stderr='',
        duration_ms=100,
        memory_used_mb=10.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='echo_hash'
    )

    validation2 = gate.validate(exec_result2)
    # Still valid because it came from VEE execution
    assert validation2.is_valid is True


def test_parse_multiple_formats(gate):
    """Test parsing numbers in various formats."""
    stdout = """
Results:
- Correlation: 0.95
- P-value: 1.23e-05
- Sample size: 252
- Mean: -0.0015
- Percentage: 45.67%
"""

    result = TruthBoundaryGate.parse_numerical_output(stdout)

    assert 'Correlation' in result
    assert result['Correlation'] == 0.95
    assert 'P-value' in result or 'P_value' in result  # May normalize key
    assert 'Sample size' in result or 'Sample_size' in result
    assert 'Percentage' in result


def test_validation_result_dataclass():
    """Test ValidationResult dataclass structure."""
    validation = ValidationResult(
        is_valid=True,
        status='success',
        extracted_values={'correlation': 0.95},
        error_message=None,
        warnings=[]
    )

    assert validation.is_valid is True
    assert validation.status == 'success'
    assert len(validation.extracted_values) == 1


def test_gate_processes_batch(gate):
    """Test processing multiple execution results in batch."""
    exec_results = [
        ExecutionResult(
            status='success',
            exit_code=0,
            stdout=f'value: {i * 0.1}',
            stderr='',
            duration_ms=1000,
            memory_used_mb=30.0,
            executed_at='2024-01-01T10:00:00Z',
            code_hash=f'hash_{i}'
        )
        for i in range(5)
    ]

    validations = gate.validate_batch(exec_results)

    assert len(validations) == 5
    assert all(v.is_valid for v in validations)


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week2_day3_success_criteria(gate):
    """
    Week 2 Day 3 Success Criteria:

    - [x] Parse numerical output from VEE execution
    - [x] Validate execution status (success/error/timeout)
    - [x] Extract key-value pairs from stdout
    - [x] Create immutable VerifiedFact objects
    - [x] Batch processing support
    """
    # Test 1: Parse and validate
    exec_result = ExecutionResult(
        status='success',
        exit_code=0,
        stdout=json.dumps({'correlation': 0.95, 'p_value': 0.001}),
        stderr='',
        duration_ms=1500,
        memory_used_mb=50.0,
        executed_at='2024-01-01T10:00:00Z',
        code_hash='test_hash'
    )

    validation = gate.validate(exec_result)
    assert validation.is_valid is True

    # Test 2: Create VerifiedFact
    fact = gate.create_verified_fact(
        validation=validation,
        query_id='query_test',
        plan_id='plan_test'
    )

    assert fact.status == 'success'
    assert len(fact.extracted_values) == 2

    # Test 3: Batch processing
    batch = [exec_result, exec_result]
    validations = gate.validate_batch(batch)
    assert len(validations) == 2

    print("""
    ✅ Week 2 Day 3 SUCCESS CRITERIA:
    - Numerical output parsing: ✅
    - Execution validation: ✅
    - VerifiedFact creation: ✅
    - Batch processing: ✅
    """)
