"""
Test only compliance queries from Golden Set.

Week 14 Day 1: Quick validation of compliance fixes.
"""

import sys
import json
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from eval.run_golden_set_v2 import load_golden_set, run_query_with_orchestrator
from eval.validators import AnswerValidator


async def test_compliance_queries():
    """Run only compliance queries (gs_004, gs_011, gs_017, gs_024, gs_030)."""

    golden_set = load_golden_set()
    queries = golden_set["queries"]

    # Filter compliance queries
    compliance_queries = [q for q in queries if q["category"] == "compliance"]

    print(f"=" * 80)
    print(f"🔒 COMPLIANCE QUERIES TEST — Week 14 Day 1")
    print(f"=" * 80)
    print(f"Total compliance queries: {len(compliance_queries)}")
    print()

    results = []
    passed = 0
    failed = 0

    for i, query_data in enumerate(compliance_queries, 1):
        query_id = query_data["id"]
        query_text = query_data["query"]
        expected = query_data["expected_answer"]

        print(f"\n{'='*80}")
        print(f"🔹 Query {query_id}: {query_text[:70]}...")
        print(f"   Expected: {expected.get('must_contain', [])}")

        try:
            result = await run_query_with_orchestrator(query_text, query_id)

            # Extract answer
            if hasattr(result, 'arbiter_response') and hasattr(result.arbiter_response, 'analysis'):
                answer_text = result.arbiter_response.analysis
            else:
                answer_text = str(result)

            # Extract validation fields
            source_verified = getattr(result, 'source_verified', True)
            error_detected = getattr(result, 'error_detected', False)
            ambiguity_detected = getattr(result, 'ambiguity_detected', False)

            # Validate
            is_correct, validation_reason = AnswerValidator.validate_answer(
                answer_text,
                expected,
                source_verified=source_verified,
                error_detected=error_detected,
                ambiguity_detected=ambiguity_detected
            )

            if is_correct:
                print(f"   ✅ PASS: {validation_reason}")
                passed += 1
            else:
                print(f"   ❌ FAIL: {validation_reason}")
                print(f"   Answer: {answer_text[:200]}...")
                failed += 1

            results.append({
                "query_id": query_id,
                "query": query_text,
                "answer": answer_text[:500],
                "expected": expected,
                "is_correct": is_correct,
                "validation_reason": validation_reason
            })

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            failed += 1
            results.append({
                "query_id": query_id,
                "query": query_text,
                "error": str(e),
                "is_correct": False
            })

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 COMPLIANCE QUERIES SUMMARY")
    print(f"={'='*80}")
    print(f"✅ Passed: {passed}/{len(compliance_queries)} ({passed/len(compliance_queries)*100:.1f}%)")
    print(f"❌ Failed: {failed}/{len(compliance_queries)}")
    print()

    # Save results
    output_file = project_root / "results" / "compliance_test_results.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": "2026-02-14T23:50:00Z",
            "total": len(compliance_queries),
            "passed": passed,
            "failed": failed,
            "accuracy": passed / len(compliance_queries),
            "results": results
        }, f, indent=2)

    print(f"💾 Results saved to: {output_file}")

    # Exit code
    return 0 if passed == len(compliance_queries) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_compliance_queries())
    sys.exit(exit_code)
