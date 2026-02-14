"""
Night Audit для APE 2026
Запуск: python night_audit.py
Длительность: ~15-20 минут
"""
import os
import subprocess
import json
from datetime import datetime

print("🌙 Starting night audit at", datetime.now())

os.makedirs("audit_results", exist_ok=True)

def run_command(name, cmd, output_file):
    print(f"{name}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        with open(f"audit_results/{output_file}", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)
        print(f"  ✅ {output_file}")
        return True
    except Exception as e:
        print(f"  ⚠️  Failed: {e}")
        return False

# 1. Test coverage (most important)
run_command("1/6 Test coverage", 
    "pytest --cov=src --cov-report=html --cov-report=json --cov-report=term -q",
    "coverage.txt")

# 2. Linting
run_command("2/6 Linting (ruff)",
    "ruff check src/ --output-format=json",
    "ruff.json")

# 3. Type checking
run_command("3/6 Type checking (mypy)",
    "mypy src/ --ignore-missing-imports",
    "mypy.txt")

# 4. Security (if bandit installed)
run_command("4/6 Security audit (bandit)",
    "bandit -r src/ -ll -f json",
    "security.json")

# 5. Dependencies (if pip-audit installed)
run_command("5/6 Dependency audit",
    "pip-audit --format json",
    "dependencies.json")

# 6. Git health
print("6/6 Git health...")
subprocess.run("git status --porcelain | findstr /R \"^??\" > audit_results\untracked.txt", shell=True)

# Create summary
print("Creating summary...")
summary = {
    "timestamp": datetime.now().isoformat(),
    "coverage_pct": 0.0,
    "security_issues": 0,
    "vulnerabilities": 0,
    "ruff_errors": 0,
}

# Parse coverage
if os.path.exists("coverage.json"):
    with open("coverage.json") as f:
        data = json.load(f)
        summary["coverage_pct"] = data["totals"]["percent_covered"]

# Parse security
if os.path.exists("audit_results/security.json"):
    try:
        with open("audit_results/security.json") as f:
            data = json.load(f)
            summary["security_issues"] = len(data.get("results", []))
    except:
        pass

# Parse dependencies
if os.path.exists("audit_results/dependencies.json"):
    try:
        with open("audit_results/dependencies.json") as f:
            data = json.load(f)
            summary["vulnerabilities"] = len(data.get("vulnerabilities", []))
    except:
        pass

# Parse ruff
if os.path.exists("audit_results/ruff.json"):
    try:
        with open("audit_results/ruff.json") as f:
            data = json.load(f)
            summary["ruff_errors"] = len(data)
    except:
        pass

# Write summary
with open("audit_results/SUMMARY.md", "w") as f:
    f.write("# Night Audit Summary\n\n")
    f.write(f"**Date:** {summary['timestamp']}\n\n")
    f.write(f"## Critical Issues\n")
    f.write(f"- Security issues: {summary['security_issues']}\n")
    f.write(f"- Vulnerabilities: {summary['vulnerabilities']}\n\n")
    f.write(f"## Quality Metrics\n")
    f.write(f"- Test coverage: {summary['coverage_pct']:.1f}%\n")
    f.write(f"- Ruff errors: {summary['ruff_errors']}\n\n")
    
    critical = summary["security_issues"] + summary["vulnerabilities"]
    status = "🔴 CRITICAL" if critical > 0 else "🟢 OK"
    f.write(f"## Status: {status}\n\n")
    
    if critical > 0:
        f.write("**ACTION REQUIRED:** Fix critical issues before launch!\n")
    else:
        f.write("**All clear!** Ready to proceed with Phase 1 tomorrow.\n")

print("\n✅ Night audit completed!")
print("📊 Results: audit_results/")
print("📄 Summary: audit_results/SUMMARY.md")
print("\n🌙 Good night! See you tomorrow.")
