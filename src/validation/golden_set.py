"""
Golden Set Validator for APE 2026.

Validates system accuracy against a curated set of financial queries
with known correct answers. Critical for ensuring zero hallucination guarantee.

Week 9 Day 3: Production Readiness - Golden Set Validation Framework
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single query against golden set."""
    query_id: str
    query_text: str
    expected_value: float
    actual_value: Optional[float]
    tolerance: float
    is_within_tolerance: bool
    absolute_error: Optional[float]
    relative_error: Optional[float]
    confidence_score: Optional[float]
    confidence_in_range: bool
    execution_time_seconds: float
    vee_executed: bool
    source_verified: bool  # True if value came from VEE, not LLM hallucination
    temporal_compliance: bool  # No look-ahead bias
    status: str  # "PASS", "FAIL", "ERROR"
    error_message: Optional[str] = None


@dataclass
class GoldenSetReport:
    """Aggregated results from running full golden set."""
    total_queries: int
    passed: int
    failed: int
    errors: int
    accuracy: float  # passed / total
    hallucination_count: int  # Queries where LLM made up numbers
    hallucination_rate: float  # hallucination_count / total
    temporal_violations: int  # Look-ahead bias detected
    avg_absolute_error: float
    avg_relative_error: float
    avg_confidence: float
    avg_execution_time: float
    results_by_category: Dict[str, Dict[str, int]]
    failed_queries: List[Dict]
    timestamp: str


class GoldenSetValidator:
    """
    Validator for testing APE system against golden set of queries.

    The golden set contains financial queries with pre-computed expected values
    from authoritative sources (yfinance + manual verification).
    """

    def __init__(self, golden_set_path: str = "tests/golden_set/financial_queries_v1.json"):
        """
        Initialize validator.

        Args:
            golden_set_path: Path to golden set JSON file
        """
        self.golden_set_path = Path(golden_set_path)
        self.golden_set = self._load_golden_set()

        logger.info(
            f"Golden Set loaded: {self.golden_set['total_queries']} queries "
            f"across {len(self.golden_set['categories'])} categories"
        )

    def _load_golden_set(self) -> Dict:
        """Load golden set from JSON file."""
        if not self.golden_set_path.exists():
            raise FileNotFoundError(f"Golden set not found: {self.golden_set_path}")

        with open(self.golden_set_path, 'r') as f:
            data = json.load(f)

        return data

    def validate_single_query(
        self,
        query_data: Dict,
        actual_value: Optional[float],
        confidence_score: Optional[float],
        execution_time: float,
        vee_executed: bool,
        source_verified: bool,
        temporal_compliance: bool
    ) -> ValidationResult:
        """
        Validate a single query result against expected value.

        Args:
            query_data: Query metadata from golden set
            actual_value: Value returned by APE system
            confidence_score: Confidence score from system
            execution_time: Time taken to execute query
            vee_executed: Whether VEE sandbox was actually executed
            source_verified: Whether value came from VEE (not hallucination)
            temporal_compliance: No future data was used

        Returns:
            ValidationResult with pass/fail status
        """
        query_id = query_data["id"]
        expected_value = query_data["expected_value"]
        tolerance = query_data["tolerance"]
        confidence_range = query_data["confidence_range"]

        # Check if value is available
        if actual_value is None:
            return ValidationResult(
                query_id=query_id,
                query_text=query_data["query"],
                expected_value=expected_value,
                actual_value=None,
                tolerance=tolerance,
                is_within_tolerance=False,
                absolute_error=None,
                relative_error=None,
                confidence_score=confidence_score,
                confidence_in_range=False,
                execution_time_seconds=execution_time,
                vee_executed=vee_executed,
                source_verified=source_verified,
                temporal_compliance=temporal_compliance,
                status="ERROR",
                error_message="No value returned by system"
            )

        # Calculate errors
        absolute_error = abs(actual_value - expected_value)
        relative_error = absolute_error / abs(expected_value) if expected_value != 0 else float('inf')

        # Check tolerance
        is_within_tolerance = absolute_error <= tolerance

        # Check confidence range
        confidence_in_range = False
        if confidence_score is not None:
            confidence_in_range = confidence_range[0] <= confidence_score <= confidence_range[1]

        # Determine status
        if not source_verified:
            status = "FAIL"
            error_msg = "HALLUCINATION: Value not from VEE execution"
        elif not temporal_compliance:
            status = "FAIL"
            error_msg = "TEMPORAL_VIOLATION: Look-ahead bias detected"
        elif not is_within_tolerance:
            status = "FAIL"
            error_msg = f"OUT_OF_TOLERANCE: |{actual_value} - {expected_value}| = {absolute_error:.3f} > {tolerance}"
        else:
            status = "PASS"
            error_msg = None

        return ValidationResult(
            query_id=query_id,
            query_text=query_data["query"],
            expected_value=expected_value,
            actual_value=actual_value,
            tolerance=tolerance,
            is_within_tolerance=is_within_tolerance,
            absolute_error=absolute_error,
            relative_error=relative_error,
            confidence_score=confidence_score,
            confidence_in_range=confidence_in_range,
            execution_time_seconds=execution_time,
            vee_executed=vee_executed,
            source_verified=source_verified,
            temporal_compliance=temporal_compliance,
            status=status,
            error_message=error_msg
        )

    def run_validation(
        self,
        query_executor_func,
        category_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> GoldenSetReport:
        """
        Run validation on golden set queries.

        Args:
            query_executor_func: Function that takes query string and returns:
                (actual_value, confidence, exec_time, vee_executed, source_verified, temporal_compliance)
            category_filter: Optional category to test (e.g., "sharpe_ratio")
            limit: Optional limit on number of queries to test

        Returns:
            GoldenSetReport with aggregated results
        """
        queries = self.golden_set["queries"]

        # Apply filters
        if category_filter:
            queries = [q for q in queries if q["category"] == category_filter]

        if limit:
            queries = queries[:limit]

        logger.info(f"Running validation on {len(queries)} queries...")

        results = []
        for i, query_data in enumerate(queries, 1):
            logger.info(f"[{i}/{len(queries)}] Testing: {query_data['id']}")

            try:
                # Execute query through system
                result = query_executor_func(query_data["query"])

                # Unpack result
                actual_value, confidence, exec_time, vee_executed, source_verified, temporal_compliance = result

                # Validate
                validation_result = self.validate_single_query(
                    query_data,
                    actual_value,
                    confidence,
                    exec_time,
                    vee_executed,
                    source_verified,
                    temporal_compliance
                )

                results.append(validation_result)

                # Log status
                if validation_result.status == "PASS":
                    logger.info(f"  ✅ PASS: {actual_value:.3f} ≈ {validation_result.expected_value:.3f}")
                else:
                    logger.warning(
                        f"  ❌ {validation_result.status}: {validation_result.error_message}"
                    )

            except Exception as e:
                logger.error(f"  ❌ ERROR: {e}")
                results.append(ValidationResult(
                    query_id=query_data["id"],
                    query_text=query_data["query"],
                    expected_value=query_data["expected_value"],
                    actual_value=None,
                    tolerance=query_data["tolerance"],
                    is_within_tolerance=False,
                    absolute_error=None,
                    relative_error=None,
                    confidence_score=None,
                    confidence_in_range=False,
                    execution_time_seconds=0.0,
                    vee_executed=False,
                    source_verified=False,
                    temporal_compliance=False,
                    status="ERROR",
                    error_message=str(e)
                ))

        # Generate report
        return self._generate_report(results, queries)

    def _generate_report(self, results: List[ValidationResult], queries: List[Dict]) -> GoldenSetReport:
        """Generate aggregated report from validation results."""
        total = len(results)
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        errors = sum(1 for r in results if r.status == "ERROR")

        accuracy = passed / total if total > 0 else 0.0

        # Count hallucinations
        hallucination_count = sum(1 for r in results if not r.source_verified)
        hallucination_rate = hallucination_count / total if total > 0 else 0.0

        # Count temporal violations
        temporal_violations = sum(1 for r in results if not r.temporal_compliance)

        # Calculate averages (only for valid results)
        valid_results = [r for r in results if r.actual_value is not None]

        avg_abs_error = sum(r.absolute_error for r in valid_results) / len(valid_results) if valid_results else 0.0
        avg_rel_error = sum(r.relative_error for r in valid_results) / len(valid_results) if valid_results else 0.0

        results_with_confidence = [r for r in results if r.confidence_score is not None]
        avg_confidence = sum(r.confidence_score for r in results_with_confidence) / len(results_with_confidence) if results_with_confidence else 0.0

        avg_exec_time = sum(r.execution_time_seconds for r in results) / total if total > 0 else 0.0

        # Results by category
        results_by_category = {}
        for query in queries:
            category = query["category"]
            if category not in results_by_category:
                results_by_category[category] = {"total": 0, "passed": 0, "failed": 0}

            results_by_category[category]["total"] += 1

            # Find corresponding result
            result = next((r for r in results if r.query_id == query["id"]), None)
            if result:
                if result.status == "PASS":
                    results_by_category[category]["passed"] += 1
                else:
                    results_by_category[category]["failed"] += 1

        # Failed queries details
        failed_queries = [
            {
                "query_id": r.query_id,
                "query": r.query_text,
                "expected": r.expected_value,
                "actual": r.actual_value,
                "error": r.error_message,
                "status": r.status
            }
            for r in results if r.status != "PASS"
        ]

        return GoldenSetReport(
            total_queries=total,
            passed=passed,
            failed=failed,
            errors=errors,
            accuracy=accuracy,
            hallucination_count=hallucination_count,
            hallucination_rate=hallucination_rate,
            temporal_violations=temporal_violations,
            avg_absolute_error=avg_abs_error,
            avg_relative_error=avg_rel_error,
            avg_confidence=avg_confidence,
            avg_execution_time=avg_exec_time,
            results_by_category=results_by_category,
            failed_queries=failed_queries,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    def save_report(self, report: GoldenSetReport, output_path: str):
        """Save validation report to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)

        logger.info(f"Report saved to: {output_path}")

    def print_report(self, report: GoldenSetReport):
        """Print human-readable report to console."""
        print("\n" + "=" * 80)
        print("GOLDEN SET VALIDATION REPORT")
        print("=" * 80)
        print(f"\n📊 Overall Results:")
        print(f"  Total Queries: {report.total_queries}")
        print(f"  Passed: {report.passed} ({report.accuracy * 100:.1f}%)")
        print(f"  Failed: {report.failed}")
        print(f"  Errors: {report.errors}")
        print(f"\n🎯 Quality Metrics:")
        print(f"  Accuracy: {report.accuracy * 100:.1f}%")
        print(f"  Hallucination Rate: {report.hallucination_rate * 100:.2f}% ({report.hallucination_count} queries)")
        print(f"  Temporal Violations: {report.temporal_violations}")
        print(f"  Avg Absolute Error: {report.avg_absolute_error:.4f}")
        print(f"  Avg Relative Error: {report.avg_relative_error * 100:.2f}%")
        print(f"  Avg Confidence: {report.avg_confidence:.3f}")
        print(f"  Avg Execution Time: {report.avg_execution_time:.2f}s")

        print(f"\n📋 Results by Category:")
        for category, stats in report.results_by_category.items():
            accuracy = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {category}: {stats['passed']}/{stats['total']} ({accuracy:.1f}%)")

        if report.failed_queries:
            print(f"\n❌ Failed Queries ({len(report.failed_queries)}):")
            for fq in report.failed_queries[:10]:  # Show first 10
                print(f"  [{fq['query_id']}] {fq['query']}")
                print(f"    Expected: {fq['expected']}, Actual: {fq['actual']}")
                print(f"    Error: {fq['error']}")

        print("\n" + "=" * 80)
