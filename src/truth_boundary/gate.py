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


@dataclass
class VerifiedFact:
    """
    Verified fact from code execution.

    All numerical values are guaranteed to come from VEE execution,
    not LLM hallucination.

    Week 5 Day 3: Made mutable to allow confidence adjustment via Debate.
    Core numerical values remain immutable by design.
    
    Week 11: Added data attribution fields for compliance (SEC/FINRA).
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

    # Week 5 Day 3: Added for Debate System integration
    source_code: Optional[str] = None
    confidence_score: float = 1.0  # Default high confidence before debate

    # Week 11: Data attribution for regulatory compliance
    data_source: str = "yfinance"  # Source: yfinance, alpha_vantage, polygon, cache
    data_freshness: Optional[datetime] = None  # When data was fetched from external API
    source_verified: bool = False  # Week 14: Conservative default - MUST be explicitly set by VEE execution
    
    # API response: Human-readable statement summarizing the fact
    statement: Optional[str] = None  # Generated summary for API response


@dataclass
class ValidationResult:
    """Result of validating an ExecutionResult."""

    is_valid: bool
    status: str  # 'success', 'error', 'timeout'
    extracted_values: Dict[str, Any]
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # Week 14: Propagate source_verified from ExecutionResult
    source_verified: bool = False  # From VEE execution validation
    error_detected: bool = False  # From VEE execution
    ambiguity_detected: bool = False  # From VEE execution


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

        Tries to parse:
        1. The entire stdout as JSON
        2. The last non-empty line as JSON
        3. Any line that looks like JSON (starts with { or [)

        Args:
            stdout: JSON string from code execution

        Returns:
            Dictionary with parsed values
        """
        if not stdout:
            return {}

        # Try parsing entire stdout first
        try:
            data = json.loads(stdout)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass

        # Try parsing last non-empty line
        lines = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
        if lines:
            try:
                data = json.loads(lines[-1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                pass

        # Try finding any line that looks like JSON
        for line in reversed(lines):
            if line.startswith('{') or line.startswith('['):
                try:
                    data = json.loads(line)
                    return data if isinstance(data, dict) else {}
                except json.JSONDecodeError:
                    continue

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
                error_message=exec_result.stderr,
                source_verified=False,  # Week 14: Execution failed
                error_detected=getattr(exec_result, 'error_detected', True),
                ambiguity_detected=getattr(exec_result, 'ambiguity_detected', False)
            )

        if exec_result.status == 'timeout':
            return ValidationResult(
                is_valid=False,
                status='timeout',
                extracted_values={},
                error_message='Execution timed out',
                source_verified=False,  # Week 14: Timeout = not verified
                error_detected=True,
                ambiguity_detected=False
            )

        # Try to parse as JSON first
        extracted = self.parse_json_output(exec_result.stdout)

        # CRITICAL: If JSON extraction found an 'error' key, treat as failure
        if extracted and 'error' in extracted:
            return ValidationResult(
                is_valid=False,
                status='error',
                extracted_values={},
                error_message=str(extracted['error']),
                source_verified=False,  # Week 14: JSON contains error
                error_detected=True,
                ambiguity_detected=False
            )

        # If no JSON found, check if stderr has errors before falling back to parsing
        if not extracted and exec_result.stderr and exec_result.stderr.strip():
            return ValidationResult(
                is_valid=False,
                status='error',
                extracted_values={},
                error_message=exec_result.stderr,
                source_verified=False,  # Week 14: stderr present
                error_detected=True,
                ambiguity_detected=getattr(exec_result, 'ambiguity_detected', False)
            )

        # If still no extracted values, try key-value pairs (fallback)
        if not extracted:
            extracted = self.parse_numerical_output(exec_result.stdout)

        # Final check: if still no values and stderr exists, it's an error
        if not extracted and exec_result.stderr and exec_result.stderr.strip():
            return ValidationResult(
                is_valid=False,
                status='error',
                extracted_values={},
                error_message=exec_result.stderr,
                source_verified=False,  # Week 14: No extracted values
                error_detected=True,
                ambiguity_detected=getattr(exec_result, 'ambiguity_detected', False)
            )

        # Week 14: SUCCESS path - propagate source_verified from ExecutionResult
        return ValidationResult(
            is_valid=True,
            status='success',
            extracted_values=extracted,
            error_message=None,
            warnings=[],
            source_verified=getattr(exec_result, 'source_verified', False),  # From VEE
            error_detected=getattr(exec_result, 'error_detected', False),
            ambiguity_detected=getattr(exec_result, 'ambiguity_detected', False)
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
        memory_used_mb: Optional[float] = None,
        source_code: Optional[str] = None,
        statement: Optional[str] = None
    ) -> VerifiedFact:
        """
        Create VerifiedFact from validation result.

        Args:
            validation: Validation result
            query_id: ID of user query
            plan_id: ID of execution plan
            code_hash: Hash of executed code (optional, from ExecutionResult)
            execution_time_ms: Execution time (optional, from ExecutionResult)
            memory_used_mb: Memory used (optional, from ExecutionResult)
            source_code: Executed source code (optional, for Debate System)
            statement: Human-readable statement summarizing the fact (optional)

        Returns:
            VerifiedFact
        """
        fact_id = str(uuid.uuid4())

        # Auto-generate statement from extracted_values if not provided
        if statement is None and validation.extracted_values:
            parts = [f"{k}: {v}" for k, v in validation.extracted_values.items()]
            statement = ", ".join(parts)

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
            error_message=validation.error_message,
            source_code=source_code,
            confidence_score=1.0,  # Default high confidence before debate
            statement=statement,
            source_verified=validation.source_verified  # Week 14: Propagate from VEE execution
        )
