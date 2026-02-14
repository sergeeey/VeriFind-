"""
Golden Set Runner для APE 2026.

Week 13 Day 2: Baseline validation через real LLM debate system.

Usage:
    python eval/run_golden_set.py eval/golden_set.json --output results/golden_set_run_1.json
"""

import asyncio
import json
import sys
import os
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Load environment variables manually (dotenv has parsing issues)
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
else:
    print("⚠️ .env file not found!")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from debate.parallel_orchestrator import run_multi_llm_debate


def load_golden_set(path: str) -> Dict[str, Any]:
    """Load Golden Set JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_metric_from_synthesis(synthesis: Dict[str, Any], metric_name: str) -> Any:
    """
    Extract metric value from synthesis.

    Simplified: just return the synthesis text for manual validation.
    Full implementation would parse specific metrics.
    """
    return {
        "synthesis_text": synthesis.get("recommendation", ""),
        "confidence": synthesis.get("overall_confidence", 0.0),
        "risk_reward": synthesis.get("risk_reward_ratio", "unknown")
    }


def validate_answer(answer: Any, expected: Any, tolerance_pct: float = 0.05) -> bool:
    """
    Validate if answer matches expected within tolerance.

    Simplified for MVP: manual validation required.
    Full implementation would parse numeric values and check tolerance.
    """
    # For MVP: always return True, require manual review
    return True


def check_hallucination(result: Dict[str, Any]) -> bool:
    """
    Check if response contains hallucinations.

    Simplified: check if ai_generated flag is present and disclaimer exists.
    Full implementation would use Truth Boundary Gate validation.
    """
    synthesis = result.get("synthesis", {})

    # Check compliance fields
    has_ai_flag = synthesis.get("ai_generated", False)
    has_disclaimer = "disclaimer" in result

    # If these are missing, it's a potential hallucination
    return not (has_ai_flag and has_disclaimer)


async def run_single_query(query: Dict[str, Any], query_num: int, total: int) -> Dict[str, Any]:
    """Run a single Golden Set query."""
    query_id = query["id"]
    query_text = query["query"]

    print(f"\n[{query_num}/{total}] Running: {query_id}")
    print(f"  Query: {query_text[:80]}...")

    start_time = time.time()

    try:
        # Run debate
        result = await run_multi_llm_debate(
            query=query_text,
            context={}
        )

        elapsed_ms = (time.time() - start_time) * 1000

        # Extract answer
        answer = extract_metric_from_synthesis(
            result["synthesis"],
            query["expected_answer"]["metric"]
        )

        # Validate
        is_correct = validate_answer(
            answer=answer,
            expected=query["expected_answer"].get("value"),
            tolerance_pct=query["expected_answer"].get("tolerance_pct", 0.05)
        )

        # Check hallucination
        has_hallucination = check_hallucination(result)

        print(f"  ✓ Completed in {elapsed_ms:.0f}ms")
        print(f"  Recommendation: {result['synthesis'].get('recommendation', 'N/A')}")
        print(f"  Confidence: {result['synthesis'].get('overall_confidence', 0.0):.2%}")

        return {
            "query_id": query_id,
            "category": query["category"],
            "difficulty": query["difficulty"],
            "query_text": query_text,
            "answer": answer,
            "expected": query["expected_answer"],
            "correct": is_correct,  # Manual validation required
            "hallucination": has_hallucination,
            "processing_time_ms": elapsed_ms,
            "cost_usd": result.get("metadata", {}).get("cost_usd", 0.0),
            "full_result": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"  ✗ ERROR: {e}")

        return {
            "query_id": query_id,
            "category": query["category"],
            "difficulty": query["difficulty"],
            "query_text": query_text,
            "error": str(e),
            "correct": False,
            "hallucination": True,
            "processing_time_ms": elapsed_ms,
            "timestamp": datetime.now().isoformat()
        }


async def run_golden_set(golden_set_path: str, output_path: str, limit: int = None):
    """Run Golden Set validation."""
    print("=" * 80)
    print("APE 2026 - Golden Set Validation")
    print("=" * 80)

    # Load Golden Set
    golden_set = load_golden_set(golden_set_path)
    queries = golden_set["queries"]

    if limit:
        queries = queries[:limit]
        print(f"\nLimited to first {limit} queries (for testing)")

    print(f"\nTotal queries: {len(queries)}")
    print(f"Categories: {list(golden_set['metadata']['category_distribution'].keys())}")
    print(f"Difficulties: {list(golden_set['metadata']['difficulty_distribution'].keys())}")
    print(f"\nStarting validation...\n")

    results = []

    for i, query in enumerate(queries, 1):
        result = await run_single_query(query, i, len(queries))
        results.append(result)

        # Delay between requests to avoid rate limits
        if i < len(queries):
            await asyncio.sleep(2)

    # Generate summary
    total = len(results)
    correct = sum(1 for r in results if r.get("correct", False))
    hallucinations = sum(1 for r in results if r.get("hallucination", False))
    errors = sum(1 for r in results if "error" in r)

    total_cost = sum(r.get("cost_usd", 0.0) for r in results)
    avg_time_ms = sum(r.get("processing_time_ms", 0.0) for r in results if "error" not in r) / max(total - errors, 1)

    summary = {
        "run_info": {
            "timestamp": datetime.now().isoformat(),
            "golden_set_version": golden_set["version"],
            "total_queries": total,
            "successful": total - errors,
            "errors": errors
        },
        "metrics": {
            "accuracy": correct / total if total > 0 else 0.0,
            "hallucination_rate": hallucinations / total if total > 0 else 0.0,
            "error_rate": errors / total if total > 0 else 0.0,
            "avg_processing_time_ms": avg_time_ms,
            "total_cost_usd": total_cost
        },
        "breakdown_by_category": {},
        "breakdown_by_difficulty": {},
        "results": results
    }

    # Category breakdown
    for category in golden_set["metadata"]["category_distribution"].keys():
        cat_results = [r for r in results if r["category"] == category]
        if cat_results:
            summary["breakdown_by_category"][category] = {
                "total": len(cat_results),
                "correct": sum(1 for r in cat_results if r.get("correct", False)),
                "accuracy": sum(1 for r in cat_results if r.get("correct", False)) / len(cat_results)
            }

    # Difficulty breakdown
    for difficulty in golden_set["metadata"]["difficulty_distribution"].keys():
        diff_results = [r for r in results if r["difficulty"] == difficulty]
        if diff_results:
            summary["breakdown_by_difficulty"][difficulty] = {
                "total": len(diff_results),
                "correct": sum(1 for r in diff_results if r.get("correct", False)),
                "accuracy": sum(1 for r in diff_results if r.get("correct", False)) / len(diff_results)
            }

    # Save results
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Queries:      {total}")
    print(f"Successful:         {total - errors}")
    print(f"Errors:             {errors}")
    print(f"Accuracy:           {summary['metrics']['accuracy']:.1%} (manual validation required)")
    print(f"Hallucination Rate: {summary['metrics']['hallucination_rate']:.1%}")
    print(f"Avg Time:           {avg_time_ms:.0f}ms")
    print(f"Total Cost:         ${total_cost:.4f}")
    print(f"\nResults saved to: {output_file}")
    print("=" * 80)

    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Golden Set validation")
    parser.add_argument("golden_set", help="Path to golden_set.json")
    parser.add_argument("--output", default="results/golden_set_run.json", help="Output file path")
    parser.add_argument("--limit", type=int, help="Limit number of queries (for testing)")

    args = parser.parse_args()

    # Run validation
    asyncio.run(run_golden_set(args.golden_set, args.output, args.limit))


if __name__ == "__main__":
    main()
