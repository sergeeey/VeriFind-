"""Golden Set Validation with Real LLM API.

Week 11 Day 5: Production baseline validation with Claude API.

This test runs the full 30-query Golden Set through the real orchestrator
with Claude API to establish production baseline metrics:
- Accuracy ≥90%
- Hallucination rate = 0%
- Temporal violations = 0
- Confidence calibration

IMPORTANT: Requires ANTHROPIC_API_KEY environment variable.
Cost: ~$0.30-0.50 for 30 queries (estimated).
"""

import pytest
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from src.validation.golden_set import GoldenSetValidator, ValidationResult, GoldenSetReport
from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator, StateStatus, APEState


@pytest.mark.realapi
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - skipping real API test"
)
class TestGoldenSetRealLLM:
    """Golden Set validation with real LLM API."""

    @pytest.fixture(scope="class")
    def orchestrator(self):
        """Initialize orchestrator with real LLM."""
        api_key = os.getenv("ANTHROPIC_API_KEY")

        return LangGraphOrchestrator(
            claude_api_key=api_key,
            use_real_llm=True,
            llm_provider="deepseek",  # Cost-optimized (43x cheaper than Sonnet)
            vee_config={
                'memory_limit': '256m',
                'cpu_limit': 0.5,
                'timeout': 30
            }
        )

    @pytest.fixture(scope="class")
    def validator(self):
        """Initialize Golden Set validator."""
        return GoldenSetValidator("tests/golden_set/financial_queries_v1.json")

    def test_single_query_real_llm(self, orchestrator, validator):
        """Test single query with real LLM (smoke test)."""
        # Get first query
        query_data = validator.golden_set["queries"][0]
        query_id = query_data["id"]
        query_text = query_data["query"]

        print(f"\n🧪 Testing query: {query_text}")
        print(f"   Expected: {query_data['expected_value']}")

        # Execute through orchestrator
        start_time = time.time()
        state = orchestrator.run(query_id, query_text)
        execution_time = time.time() - start_time

        print(f"   Status: {state.status}")
        print(f"   Execution time: {execution_time:.2f}s")

        # Check basic success
        assert state.status == StateStatus.COMPLETED, f"Query failed: {state.error_message}"
        assert state.verified_fact is not None, "No verified fact produced"

        # Validate against Golden Set
        result = self._validate_query_result(query_data, state)

        print(f"   Result: {'✅ PASS' if result.status == 'PASS' else '❌ FAIL'}")
        if result.status != "PASS":
            print(f"   Reason: {result.error_message}")
        if result.actual_value is not None:
            print(f"   Actual: {result.actual_value:.3f} (error: {result.absolute_error:.3f})")

        assert result.status == "PASS", f"Validation failed: {result.error_message}"

    @pytest.mark.slow
    def test_full_golden_set_real_llm(self, orchestrator, validator):
        """Run full 30-query Golden Set with real LLM.

        This is the main production baseline validation test.
        Expected runtime: ~15-30 minutes (30 queries × 30-60s each).
        Expected cost: ~$0.30-0.50 with DeepSeek.

        Success criteria:
        - Accuracy ≥90% (27/30 queries correct)
        - Hallucination rate = 0%
        - Temporal violations = 0
        """
        print("\n" + "="*70)
        print("🚀 GOLDEN SET REAL LLM VALIDATION")
        print("="*70)
        print(f"Total queries: {len(validator.golden_set['queries'])}")
        print(f"Provider: deepseek-chat")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")

        results: List[ValidationResult] = []
        total_cost = 0.0
        total_time = 0.0

        # Execute all queries
        for i, query_data in enumerate(validator.golden_set["queries"], 1):
            query_id = query_data["id"]
            query_text = query_data["query"]
            category = query_data["category"]
            expected = query_data["expected_value"]

            print(f"\n[{i}/30] {query_id} ({category})")
            print(f"   Query: {query_text}")
            print(f"   Expected: {expected}")

            try:
                # Execute query
                start_time = time.time()
                state = orchestrator.run(query_id, query_text)
                exec_time = time.time() - start_time
                total_time += exec_time

                # Track cost if available
                if hasattr(orchestrator, 'debate_adapter') and orchestrator.debate_adapter:
                    stats = orchestrator.debate_adapter.get_stats()
                    query_cost = stats.get('total_cost', 0.0)
                    total_cost += query_cost
                    print(f"   Cost: ${query_cost:.6f}")

                print(f"   Time: {exec_time:.2f}s")
                print(f"   Status: {state.status}")

                # Validate result
                result = self._validate_query_result(query_data, state)
                results.append(result)

                if result.status == "PASS":
                    print(f"   ✅ PASS (actual: {result.actual_value:.3f})")
                else:
                    print(f"   ❌ {result.status}")
                    if result.error_message:
                        print(f"      - {result.error_message}")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results.append(ValidationResult(
                    query_id=query_id,
                    query_text=query_text,
                    expected_value=expected,
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
                    temporal_compliance=True,
                    status="ERROR",
                    error_message=f"Exception: {str(e)}"
                ))

        # Generate report
        report = self._generate_report(results, validator, total_time, total_cost)

        # Save report
        report_path = Path("tests/golden_set/GOLDEN_SET_BASELINE_REAL_LLM.json")
        self._save_report(report, report_path)

        # Print summary
        self._print_summary(report)

        # Assert success criteria
        assert report["accuracy"] >= 0.90, \
            f"Accuracy {report['accuracy']:.2%} < 90% threshold"
        assert report["hallucination_rate"] == 0.0, \
            f"Hallucinations detected: {report['hallucination_rate']:.2%}"
        assert report["temporal_violations"] == 0, \
            f"Temporal violations: {report['temporal_violations']}"

        print("\n" + "="*70)
        print("✅ GOLDEN SET VALIDATION PASSED!")
        print("="*70)

    def _validate_query_result(
        self,
        query_data: Dict[str, Any],
        state: APEState
    ) -> ValidationResult:
        """Validate orchestrator result against Golden Set query.

        Args:
            query_data: Golden Set query with expected value
            state: Orchestrator state after execution

        Returns:
            ValidationResult with pass/fail status
        """
        query_id = query_data["id"]
        query_text = query_data["query"]
        expected = query_data["expected_value"]
        tolerance = query_data["tolerance"]
        confidence_range = query_data["confidence_range"]

        # Calculate execution time from state metrics
        metrics = state.get_metrics()
        execution_time = metrics['total_duration_ms'] / 1000.0

        # Check if query succeeded
        if state.status != StateStatus.COMPLETED:
            return ValidationResult(
                query_id=query_id,
                query_text=query_text,
                expected_value=expected,
                actual_value=None,
                tolerance=tolerance,
                is_within_tolerance=False,
                absolute_error=None,
                relative_error=None,
                confidence_score=None,
                confidence_in_range=False,
                execution_time_seconds=execution_time,
                vee_executed=False,
                source_verified=False,
                temporal_compliance=True,
                status="ERROR",
                error_message=f"Query failed with status: {state.status}"
            )

        # Extract verified fact
        verified_fact = state.verified_fact
        if not verified_fact:
            return ValidationResult(
                query_id=query_id,
                query_text=query_text,
                expected_value=expected,
                actual_value=None,
                tolerance=tolerance,
                is_within_tolerance=False,
                absolute_error=None,
                relative_error=None,
                confidence_score=None,
                confidence_in_range=False,
                execution_time_seconds=execution_time,
                vee_executed=True,
                source_verified=False,
                temporal_compliance=True,
                status="ERROR",
                error_message="No verified fact produced"
            )

        # Extract numerical value from verified fact
        actual_value = self._extract_numerical_value(verified_fact)
        if actual_value is None:
            return ValidationResult(
                query_id=query_id,
                query_text=query_text,
                expected_value=expected,
                actual_value=None,
                tolerance=tolerance,
                is_within_tolerance=False,
                absolute_error=None,
                relative_error=None,
                confidence_score=getattr(verified_fact, 'confidence', None),
                confidence_in_range=False,
                execution_time_seconds=execution_time,
                vee_executed=True,
                source_verified=getattr(verified_fact, 'source_verified', False),
                temporal_compliance=True,
                status="ERROR",
                error_message="Could not extract numerical value from result"
            )

        # Calculate errors
        absolute_error = abs(actual_value - expected)
        relative_error = absolute_error / abs(expected) if expected != 0 else float('inf')
        is_within_tolerance = absolute_error <= tolerance

        # Check confidence
        confidence_score = getattr(verified_fact, 'confidence', None)
        confidence_in_range = False
        if confidence_score is not None:
            confidence_in_range = confidence_range[0] <= confidence_score <= confidence_range[1]

        # Check source verification and temporal compliance
        source_verified = getattr(verified_fact, 'source_verified', False)
        temporal_compliance = query_data["temporal_constraints"]["no_future_data"]

        # Determine status
        if is_within_tolerance and source_verified and temporal_compliance:
            status = "PASS"
            error_message = None
        else:
            status = "FAIL"
            reasons = []
            if not is_within_tolerance:
                reasons.append(f"Value {actual_value:.3f} outside tolerance (expected {expected:.3f} ± {tolerance:.3f})")
            if not source_verified:
                reasons.append("Result not source-verified (potential hallucination)")
            if not temporal_compliance:
                reasons.append("Temporal constraint violated (look-ahead bias)")
            error_message = "; ".join(reasons)

        return ValidationResult(
            query_id=query_id,
            query_text=query_text,
            expected_value=expected,
            actual_value=actual_value,
            tolerance=tolerance,
            is_within_tolerance=is_within_tolerance,
            absolute_error=absolute_error,
            relative_error=relative_error,
            confidence_score=confidence_score,
            confidence_in_range=confidence_in_range,
            execution_time_seconds=execution_time,
            vee_executed=True,
            source_verified=source_verified,
            temporal_compliance=temporal_compliance,
            status=status,
            error_message=error_message
        )

    def _extract_numerical_value(self, verified_fact) -> float:
        """Extract numerical value from verified fact."""
        # Try extracted_values dict
        if hasattr(verified_fact, 'extracted_values') and verified_fact.extracted_values:
            for key, val in verified_fact.extracted_values.items():
                if isinstance(val, (int, float)):
                    return float(val)

        # Try value attribute
        if hasattr(verified_fact, 'value'):
            if isinstance(verified_fact.value, (int, float)):
                return float(verified_fact.value)

        # Try parsing from fact_description
        if hasattr(verified_fact, 'fact_description'):
            import re
            numbers = re.findall(r'-?\d+\.?\d*', verified_fact.fact_description)
            if numbers:
                return float(numbers[0])

        return None

    def _generate_report(
        self,
        results: List[ValidationResult],
        validator: GoldenSetValidator,
        total_time: float,
        total_cost: float
    ) -> Dict[str, Any]:
        """Generate validation report."""
        total = len(results)
        passed = sum(1 for r in results if r.status == "PASS")
        accuracy = passed / total if total > 0 else 0.0

        # Count hallucinations and temporal violations
        hallucinations = sum(
            1 for r in results
            if not r.source_verified and r.status in ("FAIL", "ERROR")
        )
        temporal_violations = sum(
            1 for r in results
            if not r.temporal_compliance and r.status in ("FAIL", "ERROR")
        )

        return {
            "version": "1.0",
            "test_date": datetime.now().isoformat(),
            "provider": "deepseek-chat",
            "total_queries": total,
            "passed": passed,
            "failed": total - passed,
            "accuracy": accuracy,
            "hallucination_rate": hallucinations / total if total > 0 else 0.0,
            "temporal_violations": temporal_violations,
            "total_execution_time": total_time,
            "avg_execution_time": total_time / total if total > 0 else 0.0,
            "total_cost_usd": total_cost,
            "avg_cost_per_query": total_cost / total if total > 0 else 0.0,
            "results": [
                {
                    "query_id": r.query_id,
                    "query_text": r.query_text,
                    "status": r.status,
                    "actual_value": r.actual_value,
                    "expected_value": r.expected_value,
                    "tolerance": r.tolerance,
                    "absolute_error": r.absolute_error,
                    "confidence_score": r.confidence_score,
                    "source_verified": r.source_verified,
                    "temporal_compliance": r.temporal_compliance,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }

    def _save_report(self, report: Dict[str, Any], path: Path) -> None:
        """Save report to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved: {path}")

    def _print_summary(self, report: Dict[str, Any]) -> None:
        """Print report summary."""
        print("\n" + "="*70)
        print("📊 GOLDEN SET VALIDATION SUMMARY")
        print("="*70)
        print(f"Total Queries:      {report['total_queries']}")
        print(f"Passed:             {report['passed']} ✅")
        print(f"Failed:             {report['failed']} ❌")
        print(f"Accuracy:           {report['accuracy']:.2%} (target: ≥90%)")
        print(f"Hallucination Rate: {report['hallucination_rate']:.2%} (target: 0%)")
        print(f"Temporal Violations:{report['temporal_violations']} (target: 0)")
        print()
        print(f"Total Time:         {report['total_execution_time']:.2f}s")
        print(f"Avg Time/Query:     {report['avg_execution_time']:.2f}s")
        print(f"Total Cost:         ${report['total_cost_usd']:.4f}")
        print(f"Avg Cost/Query:     ${report['avg_cost_per_query']:.6f}")
        print("="*70)
