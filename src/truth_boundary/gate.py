"""
Truth Boundary Gate - Validates VEE execution outputs.

Week 2 Day 3: Enforces zero-hallucination principle.

Workflow:
1. Receive ExecutionResult from VEE
2. Parse stdout to extract numerical values
3. Validate execution status
4. Create immutable VerifiedFact
5. Store in TimescaleDB (future: Week 3)

Design principles:
- All numbers must come from code execution (not LLM generation)
- VerifiedFact is immutable (frozen dataclass)
- Audit trail: code_hash, execution_time, memory_used
"""

import re
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional

from src.vee.sandbox_runner import ExecutionResult


@dataclass(frozen=True)
class VerifiedFact:
    """
    Immutable verified fact from code execution.

    All numerical values are guaranteed to come from VEE execution,
    not LLM hallucination.
    """

    fact_id: str
    query_id: str
    plan_id: str
    code_hash: str
    status: str  # 'success', 'error', 'timeout'
    extracted_values: Dict[str, Any]
    execution_time_ms: int
    memory_used_mb: float
    created_at: datetime
    error_message: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating an ExecutionResult."""

    is_valid: bool
    status: str  # 'success', 'error', 'timeout'
    extracted_values: Dict[str, Any]
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class TruthBoundaryGate:
    """
    Truth Boundary Gate - validates VEE execution outputs.

    Purpose:
    1. Enforce zero-hallucination: all numbers from code execution
    2. Parse and validate numerical outputs
    3. Create immutable VerifiedFacts for audit trail
    """

    @staticmethod
    def parse_numerical_output(stdout: str) -> Dict[str, float]:
        """
        Parse numerical values from stdout.

        Supports formats:
        - "key: value" (e.g., "correlation: 0.95")
        - "key = value" (e.g., "mean_return = 0.0234")
        - "key value" (e.g., "P-value 0.001")

        Args:
            stdout: Standard output from code execution

        Returns:
            Dictionary mapping keys to numerical values
        """
        results = {}

        # Pattern: key: value or key = value or key value
        # Matches: "correlation: 0.95", "mean = 0.02", "p_value 0.001"
        pattern = r'([a-zA-Z_][\w\s\-]*?)[\s:=]+(-?\d+\.?\d*(?:[eE][+-]?\d+)?%?)'

        matches = re.findall(pattern, stdout)

        for key, value_str in matches:
            key_clean = key.strip().replace(' ', '_').replace('-', '_')

            # Remove % if present
            value_str_clean = value_str.replace('%', '')

            try:
                value = float(value_str_clean)
                results[key_clean] = value
            except ValueError:
                # Skip invalid numbers
                continue

        return results

    @staticmethod
    def parse_json_output(stdout: str) -> Dict[str, Any]:
        """
        Parse JSON output from stdout.

        Args:
            stdout: JSON string from code execution

        Returns:
            Dictionary with parsed values
        """
        try:
            data = json.loads(stdout)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def validate(self, exec_result: ExecutionResult) -> ValidationResult:
        """
        Validate execution result and extract numerical values.

        Args:
            exec_result: Result from VEE sandbox execution

        Returns:
            ValidationResult with extracted values
        """
        # Check execution status
        if exec_result.status == 'error':
            return ValidationResult(
                is_valid=False,
                status='error',
                extracted_values={},
                error_message=exec_result.stderr
            )

        if exec_result.status == 'timeout':
            return ValidationResult(
                is_valid=False,
                status='timeout',
                extracted_values={},
                error_message='Execution timed out'
            )

        # Try to parse as JSON first
        extracted = self.parse_json_output(exec_result.stdout)

        # If not JSON, parse as key-value pairs
        if not extracted:
            extracted = self.parse_numerical_output(exec_result.stdout)

        return ValidationResult(
            is_valid=True,
            status='success',
            extracted_values=extracted,
            error_message=None,
            warnings=[]
        )

    def validate_batch(
        self,
        exec_results: List[ExecutionResult]
    ) -> List[ValidationResult]:
        """
        Validate multiple execution results in batch.

        Args:
            exec_results: List of execution results

        Returns:
            List of validation results
        """
        return [self.validate(result) for result in exec_results]

    def create_verified_fact(
        self,
        validation: ValidationResult,
        query_id: str,
        plan_id: str,
        code_hash: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        memory_used_mb: Optional[float] = None
    ) -> VerifiedFact:
        """
        Create immutable VerifiedFact from validation result.

        Args:
            validation: Validation result
            query_id: ID of user query
            plan_id: ID of execution plan
            code_hash: Hash of executed code (optional, from ExecutionResult)
            execution_time_ms: Execution time (optional, from ExecutionResult)
            memory_used_mb: Memory used (optional, from ExecutionResult)

        Returns:
            Immutable VerifiedFact
        """
        fact_id = str(uuid.uuid4())

        return VerifiedFact(
            fact_id=fact_id,
            query_id=query_id,
            plan_id=plan_id,
            code_hash=code_hash or 'unknown',
            status=validation.status,
            extracted_values=validation.extracted_values,
            execution_time_ms=execution_time_ms or 0,
            memory_used_mb=memory_used_mb or 0.0,
            created_at=datetime.now(UTC),
            error_message=validation.error_message
        )
