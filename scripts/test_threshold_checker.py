"""Quick test for threshold checker script."""
import json
import tempfile
from pathlib import Path
import subprocess
import sys

# Mock pytest report (passing all thresholds)
passing_report = {
    "summary": {
        "total": 30,
        "passed": 28,
        "failed": 2
    },
    "duration": 45.3,
    "metrics": {
        "accuracy": 0.93,  # 93% > 90% ✅
        "hallucination_rate": 0.0,  # 0% ✅
        "temporal_violations": 0  # 0 ✅
    },
    "tests": []
}

# Mock pytest report (failing thresholds)
failing_report = {
    "summary": {
        "total": 30,
        "passed": 25,
        "failed": 5
    },
    "duration": 45.3,
    "metrics": {
        "accuracy": 0.83,  # 83% < 90% ❌
        "hallucination_rate": 0.067,  # 6.7% > 0% ❌
        "temporal_violations": 2  # 2 > 0 ❌
    },
    "tests": []
}

def test_passing_report():
    """Test with passing thresholds."""
    print("🧪 Test 1: Passing report...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(passing_report, f)
        report_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, 'scripts/check_golden_set_thresholds.py', report_path],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Should pass (exit code 0)"
        assert "✅" in result.stdout, "Should show success"
        print("  ✅ PASSED (as expected)")

    finally:
        Path(report_path).unlink(missing_ok=True)

def test_failing_report():
    """Test with failing thresholds."""
    print("🧪 Test 2: Failing report...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(failing_report, f)
        report_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, 'scripts/check_golden_set_thresholds.py', report_path],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1, "Should fail (exit code 1)"
        assert "❌" in result.stdout, "Should show failure"
        print("  ❌ FAILED (as expected)")

    finally:
        Path(report_path).unlink(missing_ok=True)

if __name__ == "__main__":
    print("🚀 Testing threshold checker script...\n")
    test_passing_report()
    test_failing_report()
    print("\n✅ All tests passed!")
