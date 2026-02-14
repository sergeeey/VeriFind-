#!/bin/bash
# Night Audit for APE 2026
# Run: bash docs/NIGHT_AUDIT_TASK.sh
# Duration: ~15-20 min

cd "$(dirname "$0")/.." || exit

echo "🌙 Starting night audit at $(date)"

mkdir -p audit_results

# 1. Security audit
echo "1/8 Security audit (bandit)..."
bandit -r src/ -ll -f json -o audit_results/security.json 2>&1 || echo "Bandit not installed"

# 2. Complexity
echo "2/8 Complexity analysis (radon)..."
radon cc src/ -a -s -j > audit_results/complexity.json 2>&1 || echo "Radon not installed"

# 3. Type check
echo "3/8 Type checking (mypy)..."
mypy src/ --ignore-missing-imports > audit_results/mypy.txt 2>&1 || echo "Mypy not installed"

# 4. Coverage
echo "4/8 Test coverage (pytest)..."
pytest --cov=src --cov-report=html --cov-report=json --cov-report=term > audit_results/coverage.txt 2>&1

# 5. Dependencies
echo "5/8 Dependency audit (pip-audit)..."
pip-audit --format json > audit_results/dependencies.json 2>&1 || echo "pip-audit not installed"

# 6. Linting
echo "6/8 Linting (ruff)..."
ruff check src/ --output-format=json > audit_results/ruff.json 2>&1 || echo "Ruff not installed"

# 7. Git health
echo "7/8 Git health check..."
git status --porcelain | grep "^??" > audit_results/untracked.txt 2>&1
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print substr($0,6)}' | \
  sort --numeric-sort --key=2 | \
  tail -20 > audit_results/large_files.txt 2>&1

# 8. Summary
echo "8/8 Creating summary..."
python3 << 'PYTHON_EOF'
import json
import os

summary = {
    "security_issues": 0,
    "high_complexity": 0,
    "low_coverage_files": 0,
    "vulnerabilities": 0,
    "coverage_pct": 0.0,
}

# Security
if os.path.exists("audit_results/security.json"):
    try:
        with open("audit_results/security.json") as f:
            data = json.load(f)
            summary["security_issues"] = len(data.get("results", []))
    except:
        pass

# Coverage
if os.path.exists("coverage.json"):
    try:
        with open("coverage.json") as f:
            data = json.load(f)
            summary["coverage_pct"] = data["totals"]["percent_covered"]
            summary["low_coverage_files"] = sum(
                1 for file_data in data["files"].values()
                if file_data["summary"]["percent_covered"] < 80
            )
    except:
        pass

# Dependencies
if os.path.exists("audit_results/dependencies.json"):
    try:
        with open("audit_results/dependencies.json") as f:
            data = json.load(f)
            summary["vulnerabilities"] = len(data.get("vulnerabilities", []))
    except:
        pass

# Write summary
with open("audit_results/SUMMARY.md", "w") as f:
    f.write("# Night Audit Summary\n\n")
    f.write(f"**Date:** {os.popen('date').read().strip()}\n\n")
    f.write(f"## 🔴 Critical Issues\n")
    f.write(f"- Security issues: {summary['security_issues']}\n")
    f.write(f"- Vulnerabilities: {summary['vulnerabilities']}\n\n")
    f.write(f"## 🟡 Quality Metrics\n")
    f.write(f"- Test coverage: {summary['coverage_pct']:.1f}%\n")
    f.write(f"- Low coverage files (<80%): {summary['low_coverage_files']}\n\n")

    status = "🔴 CRITICAL" if (summary["security_issues"] + summary["vulnerabilities"]) > 0 else "🟢 OK"
    f.write(f"## Status: {status}\n")

print("✅ Summary created: audit_results/SUMMARY.md")
PYTHON_EOF

echo "✅ Night audit completed at $(date)"
echo "📊 Results in audit_results/"
echo "📄 Summary: audit_results/SUMMARY.md"
