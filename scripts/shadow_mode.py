"""
Shadow Mode Validation Script.

Week 1 Day 4-5: Run Sonnet predictions in parallel with Opus baselines
for validation and calibration.

Usage:
    python scripts/shadow_mode.py --queries queries.json --output results.json
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, UTC
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.nodes import PlanNode
from src.evaluation import SyntheticBaselineGenerator, ComparisonMetrics


def load_queries(file_path: str) -> List[Dict[str, Any]]:
    """Load queries from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def run_shadow_mode(
    queries: List[Dict[str, Any]],
    use_opus: bool = True
) -> List[Dict[str, Any]]:
    """
    Run shadow mode validation.

    Args:
        queries: List of query dicts with 'query' and optional 'context'
        use_opus: Whether to generate Opus baselines (costs $)

    Returns:
        List of results with comparisons
    """
    # Initialize nodes
    plan_node = PlanNode(model="claude-sonnet-4-5-20250929")
    baseline_gen = SyntheticBaselineGenerator() if use_opus else None

    results = []

    for i, query_dict in enumerate(queries):
        query = query_dict['query']
        context = query_dict.get('context')

        print(f"\n[{i+1}/{len(queries)}] Processing: {query}")

        result = {
            "query_id": f"shadow_{i+1}",
            "user_query": query,
            "timestamp": datetime.now(UTC).isoformat()
        }

        try:
            # Generate Sonnet plan (mock for now - no real API)
            # For MVP, we'd call plan_node.generate_plan(query, context)
            # But that requires API key, so using mock
            result["sonnet_prediction"] = {
                "prediction": f"Mock Sonnet prediction for: {query}",
                "reasoning": "Mock reasoning - would come from real API",
                "confidence": 0.75
            }

            # Generate Opus baseline (if enabled)
            if use_opus and baseline_gen:
                baseline = baseline_gen.generate_baseline(query, context)
                result["opus_baseline"] = {
                    "prediction": baseline.prediction,
                    "reasoning": baseline.reasoning,
                    "confidence": baseline.confidence,
                    "key_factors": baseline.key_factors
                }

                # Compare predictions
                comparison = ComparisonMetrics.compare_predictions(
                    result["opus_baseline"],
                    result["sonnet_prediction"]
                )

                result["comparison"] = {
                    "directional_agreement": comparison.directional_agreement,
                    "magnitude_difference_pct": comparison.magnitude_difference_pct,
                    "reasoning_overlap": comparison.reasoning_overlap_score,
                    "overall_agreement": comparison.overall_agreement_score,
                    "is_well_calibrated": comparison.is_well_calibrated
                }

            result["status"] = "success"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        results.append(result)

    return results


def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze shadow mode results."""
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]

    analysis = {
        "summary": {
            "total_queries": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) if results else 0
        }
    }

    # Aggregate comparison metrics
    if successful and "comparison" in successful[0]:
        from dataclasses import asdict
        from src.evaluation.comparison_metrics import ComparisonResult

        # Build ComparisonResult objects
        comparison_results = []
        for r in successful:
            if "comparison" in r:
                comp = r["comparison"]
                comparison_results.append(
                    ComparisonResult(
                        directional_agreement=comp.get("directional_agreement"),
                        magnitude_difference_pct=comp.get("magnitude_difference_pct"),
                        reasoning_overlap_score=comp.get("reasoning_overlap", 0.0),
                        confidence_diff=0.0,  # Not stored
                        is_well_calibrated=comp.get("is_well_calibrated", False),
                        baseline_direction=None,
                        prediction_direction=None,
                        baseline_magnitude=None,
                        prediction_magnitude=None,
                        overall_agreement_score=comp.get("overall_agreement", 0.0)
                    )
                )

        aggregated = ComparisonMetrics.aggregate_results(comparison_results)
        analysis["metrics"] = aggregated

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Run shadow mode validation")
    parser.add_argument(
        '--queries',
        type=str,
        required=True,
        help='Path to queries JSON file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='shadow_results.json',
        help='Output file path'
    )
    parser.add_argument(
        '--no-opus',
        action='store_true',
        help='Skip Opus baseline generation (testing mode)'
    )

    args = parser.parse_args()

    # Load queries
    print(f"Loading queries from {args.queries}...")
    queries = load_queries(args.queries)
    print(f"Loaded {len(queries)} queries")

    # Run shadow mode
    print("\nRunning shadow mode...")
    results = run_shadow_mode(queries, use_opus=not args.no_opus)

    # Analyze results
    analysis = analyze_results(results)

    # Save results
    output_data = {
        "metadata": {
            "run_date": datetime.now(UTC).isoformat(),
            "queries_file": args.queries,
            "opus_enabled": not args.no_opus
        },
        "results": results,
        "analysis": analysis
    }

    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✅ Results saved to {args.output}")
    print(f"\nSummary:")
    print(f"  Total queries: {analysis['summary']['total_queries']}")
    print(f"  Success rate: {analysis['summary']['success_rate']:.1%}")

    if 'metrics' in analysis:
        print(f"\nMetrics:")
        for key, value in analysis['metrics'].items():
            print(f"  {key}: {value:.3f}")


if __name__ == '__main__':
    main()
