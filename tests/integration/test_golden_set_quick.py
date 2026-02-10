"""
Quick Golden Set test - first 5 queries only.
Week 11 Day 5: Rapid validation of pipeline.
"""

import pytest
import time
from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator
from src.validation.golden_set import GoldenSetValidator


class TestGoldenSetQuick:
    """Quick test of first 5 Golden Set queries."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return LangGraphOrchestrator()

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return GoldenSetValidator()

    def test_first_5_queries(self, orchestrator, validator):
        """Test first 5 queries for quick validation."""
        queries = validator.golden_set['queries'][:5]  # Only first 5

        print(f"\n🚀 Testing {len(queries)} queries")
        print("=" * 60)

        results = []

        for i, query_data in enumerate(queries, 1):
            print(f"\n🧪 Query {i}/{len(queries)}: {query_data['query']}")
            print(f"   Expected: {query_data['expected_value']}")

            start_time = time.time()

            try:
                state = orchestrator.run(
                    query_id=query_data['id'],
                    query_text=query_data['query'],
                    use_plan=True  # Use PLAN node
                )
                execution_time = time.time() - start_time

                print(f"   Status: {state.status.value}")
                print(f"   Time: {execution_time:.2f}s")

                result = {
                    'query_id': query_data['id'],
                    'status': state.status.value,
                    'time': execution_time,
                    'expected': query_data['expected_value']
                }

                if state.status.value == 'completed':
                    # Extract actual result from verified_fact.extracted_values
                    actual_value = None
                    if hasattr(state, 'verified_fact') and state.verified_fact:
                        extracted = state.verified_fact.extracted_values
                        if extracted:
                            # Try to find numeric value in extracted_values
                            # It could be under keys like 'sharpe_ratio', 'result', 'value', etc.
                            for key in ['sharpe_ratio', 'result', 'value', 'answer']:
                                if key in extracted:
                                    try:
                                        actual_value = float(extracted[key])
                                        result['actual'] = actual_value

                                        # Calculate accuracy
                                        expected = float(query_data['expected_value'])
                                        error_pct = abs((actual_value - expected) / expected * 100) if expected != 0 else 0
                                        result['error_pct'] = error_pct

                                        print(f"   Actual: {actual_value:.3f}")
                                        print(f"   Error: {error_pct:.1f}%")

                                        if error_pct < 10:
                                            print(f"   ✅ COMPLETED (accurate)")
                                        else:
                                            print(f"   ⚠️  COMPLETED (high error)")
                                        break
                                    except (ValueError, TypeError, KeyError):
                                        continue

                            if actual_value is None:
                                # Fallback: try to get any numeric value
                                for v in extracted.values():
                                    try:
                                        actual_value = float(v)
                                        result['actual'] = actual_value
                                        print(f"   Actual: {actual_value:.3f} (found in extracted_values)")
                                        break
                                    except (ValueError, TypeError):
                                        continue

                        if actual_value is None:
                            print(f"   ✅ COMPLETED (extracted_values: {extracted})")
                    else:
                        print(f"   ✅ COMPLETED (no verified_fact)")
                else:
                    print(f"   ❌ FAILED: {state.error_message if hasattr(state, 'error_message') else 'Unknown error'}")
                    result['error'] = state.error_message if hasattr(state, 'error_message') else 'Unknown'

                results.append(result)

            except Exception as e:
                execution_time = time.time() - start_time
                print(f"   ❌ ERROR: {str(e)[:100]}")

                results.append({
                    'query_id': query_data['id'],
                    'status': 'error',
                    'time': execution_time,
                    'error': str(e)
                })

        # Summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)

        completed = sum(1 for r in results if r['status'] == 'completed')
        total_time = sum(r['time'] for r in results)

        print(f"Completed: {completed}/{len(results)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time: {total_time/len(results):.2f}s")

        # Accuracy metrics
        results_with_accuracy = [r for r in results if 'error_pct' in r]
        if results_with_accuracy:
            avg_error = sum(r['error_pct'] for r in results_with_accuracy) / len(results_with_accuracy)
            accurate = sum(1 for r in results_with_accuracy if r['error_pct'] < 10)
            print(f"\nAccuracy:")
            print(f"  Average error: {avg_error:.1f}%")
            print(f"  Accurate (<10% error): {accurate}/{len(results_with_accuracy)}")

        # At least 1 should complete successfully
        assert completed >= 1, f"Expected at least 1 completed, got {completed}"
