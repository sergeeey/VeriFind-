#!/usr/bin/env python3
"""
Check Golden Set validation thresholds.

Week 11: CI/CD quality gates for production deployment.

Thresholds:
- Accuracy: ≥90%
- Hallucination Rate: 0%
- Temporal Violations: 0

Exit codes:
- 0: All thresholds met
- 1: One or more thresholds failed
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple


# Quality thresholds
THRESHOLDS = {
    "accuracy": 0.90,  # 90% minimum
    "hallucination_rate": 0.0,  # 0% - zero tolerance
    "temporal_violations": 0,  # 0 violations
}


def load_report(report_path: str) -> Dict[str, Any]:
    """Load pytest JSON report."""
    try:
        with open(report_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Report file not found: {report_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in report: {e}")
        sys.exit(1)


def extract_metrics(report: Dict[str, Any]) -> Dict[str, float]:
    """Extract quality metrics from pytest report.

    Looks for metrics in:
    1. report['metrics'] (if validator exports them)
    2. Calculated from test results
    """
    metrics = {}

    # Try to get pre-calculated metrics
    if 'metrics' in report:
        return report['metrics']

    # Calculate from test results
    summary = report.get('summary', {})
    total = summary.get('total', 0)
    passed = summary.get('passed', 0)

    if total > 0:
        metrics['accuracy'] = passed / total
    else:
        metrics['accuracy'] = 0.0

    # Count hallucinations and temporal violations from test failures
    metrics['hallucination_rate'] = 0.0
    metrics['temporal_violations'] = 0

    for test in report.get('tests', []):
        if test.get('outcome') == 'failed':
            # Check failure message for hallucination or temporal violation
            call = test.get('call', {})
            longrepr = call.get('longrepr', '')

            if 'hallucination' in longrepr.lower():
                metrics['hallucination_rate'] += 1.0 / total if total > 0 else 0

            if 'temporal' in longrepr.lower() or 'look-ahead' in longrepr.lower():
                metrics['temporal_violations'] += 1

    return metrics


def check_thresholds(metrics: Dict[str, float]) -> Tuple[bool, List[str]]:
    """Check if metrics meet thresholds.

    Returns:
        (all_passed, failures)
    """
    failures = []

    # Check accuracy
    accuracy = metrics.get('accuracy', 0.0)
    if accuracy < THRESHOLDS['accuracy']:
        failures.append(
            f"Accuracy: {accuracy:.2%} < {THRESHOLDS['accuracy']:.2%} (threshold)"
        )

    # Check hallucination rate
    hallucination_rate = metrics.get('hallucination_rate', 0.0)
    if hallucination_rate > THRESHOLDS['hallucination_rate']:
        failures.append(
            f"Hallucination Rate: {hallucination_rate:.2%} > {THRESHOLDS['hallucination_rate']:.2%} (threshold)"
        )

    # Check temporal violations
    temporal_violations = metrics.get('temporal_violations', 0)
    if temporal_violations > THRESHOLDS['temporal_violations']:
        failures.append(
            f"Temporal Violations: {temporal_violations} > {THRESHOLDS['temporal_violations']} (threshold)"
        )

    return len(failures) == 0, failures


def generate_summary(
    report: Dict[str, Any],
    metrics: Dict[str, float],
    passed: bool,
    failures: List[str]
) -> str:
    """Generate markdown summary."""
    summary_lines = []

    # Header
    if passed:
        summary_lines.append("## ✅ Golden Set Validation PASSED\n")
    else:
        summary_lines.append("## ❌ Golden Set Validation FAILED\n")

    # Test statistics
    summary_stat = report.get('summary', {})
    summary_lines.append("### 📊 Test Results\n")
    summary_lines.append(f"- **Total Tests:** {summary_stat.get('total', 0)}")
    summary_lines.append(f"- **Passed:** {summary_stat.get('passed', 0)} ✅")
    summary_lines.append(f"- **Failed:** {summary_stat.get('failed', 0)} {'❌' if summary_stat.get('failed', 0) > 0 else ''}")
    summary_lines.append(f"- **Duration:** {report.get('duration', 0):.2f}s\n")

    # Quality metrics
    summary_lines.append("### 🎯 Quality Metrics\n")

    accuracy = metrics.get('accuracy', 0.0)
    accuracy_pass = accuracy >= THRESHOLDS['accuracy']
    summary_lines.append(
        f"- **Accuracy:** {accuracy:.2%} "
        f"{'✅' if accuracy_pass else '❌'} "
        f"(threshold: {THRESHOLDS['accuracy']:.2%})"
    )

    hallucination_rate = metrics.get('hallucination_rate', 0.0)
    hallucination_pass = hallucination_rate <= THRESHOLDS['hallucination_rate']
    summary_lines.append(
        f"- **Hallucination Rate:** {hallucination_rate:.2%} "
        f"{'✅' if hallucination_pass else '❌'} "
        f"(threshold: {THRESHOLDS['hallucination_rate']:.2%})"
    )

    temporal_violations = metrics.get('temporal_violations', 0)
    temporal_pass = temporal_violations <= THRESHOLDS['temporal_violations']
    summary_lines.append(
        f"- **Temporal Violations:** {temporal_violations} "
        f"{'✅' if temporal_pass else '❌'} "
        f"(threshold: {THRESHOLDS['temporal_violations']})\n"
    )

    # Failures (if any)
    if failures:
        summary_lines.append("### ❌ Threshold Failures\n")
        for failure in failures:
            summary_lines.append(f"- {failure}")
        summary_lines.append("")

    # Recommendations
    if not passed:
        summary_lines.append("### 💡 Recommendations\n")

        if not accuracy_pass:
            summary_lines.append(
                "- **Low Accuracy:** Review failed test cases and improve query handling"
            )

        if not hallucination_pass:
            summary_lines.append(
                "- **Hallucinations Detected:** Check PLAN node output and VEE validation"
            )

        if not temporal_pass:
            summary_lines.append(
                "- **Temporal Violations:** Review code for look-ahead bias (e.g., .shift(-N))"
            )
        summary_lines.append("")

    return "\n".join(summary_lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_golden_set_thresholds.py <report.json>")
        sys.exit(1)

    report_path = sys.argv[1]

    print(f"📋 Loading report: {report_path}")
    report = load_report(report_path)

    print("📊 Extracting metrics...")
    metrics = extract_metrics(report)

    print("🎯 Checking thresholds...")
    passed, failures = check_thresholds(metrics)

    # Generate summary
    summary = generate_summary(report, metrics, passed, failures)

    # Write summary to file
    summary_path = Path(report_path).parent / "golden-set-summary.md"
    with open(summary_path, 'w') as f:
        f.write(summary)

    print(f"📝 Summary written to: {summary_path}")

    # Print to console
    print("\n" + "=" * 60)
    print(summary)
    print("=" * 60 + "\n")

    # Exit with appropriate code
    if passed:
        print("✅ All thresholds met!")
        sys.exit(0)
    else:
        print("❌ One or more thresholds failed")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)


if __name__ == "__main__":
    main()
