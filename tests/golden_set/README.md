# Golden Set Validation Framework

**Status:** ✅ Production Ready
**Version:** 1.0
**Date:** 2026-02-08

---

## Overview

The Golden Set is a curated collection of **30 financial queries** with pre-computed expected values, used to validate the APE 2026 system's accuracy and ensure **zero hallucination guarantee**.

### Critical Requirements

| Requirement | Threshold | Purpose |
|-------------|-----------|---------|
| **Accuracy** | ≥ 90% | Ensure reliable financial calculations |
| **Hallucination Rate** | = 0% | Prevent LLM from fabricating numbers |
| **Temporal Compliance** | 100% | No look-ahead bias in historical data |

### Dataset Composition

| Category | Queries | Metrics |
|----------|---------|---------|
| **Sharpe Ratio** | 10 | Risk-adjusted returns (SPY, QQQ, AAPL, MSFT, GOOGL, TSLA, VTI) |
| **Correlation** | 10 | Asset pair correlations (SPY-QQQ, SPY-TLT, AAPL-MSFT, etc.) |
| **Volatility** | 5 | Annualized volatility (SPY, QQQ, AAPL, TSLA, BND) |
| **Beta** | 5 | Market beta (AAPL, MSFT, TSLA, KO, QQQ vs SPY) |

**Data Source:** yfinance (Python)
**Time Period:** 2021-2023
**Reference Date:** 2024-01-15

---

## Files Structure

```
tests/golden_set/
├── README.md                      # This file
├── financial_queries_v1.json      # 30 queries with expected values
├── compute_expected_values.py     # Script to regenerate golden set
└── example_report.json            # Sample validation report
```

```
src/validation/
└── golden_set.py                  # GoldenSetValidator class
```

```
tests/unit/
└── test_golden_set.py             # 16 unit tests
```

---

## Usage

### 1. Basic Validation

```python
from src.validation.golden_set import GoldenSetValidator

# Initialize validator
validator = GoldenSetValidator("tests/golden_set/financial_queries_v1.json")

# Define query executor
def my_orchestrator(query: str):
    """
    Execute query through APE system.

    Returns:
        Tuple of (value, confidence, time, vee_executed, source_verified, temporal_compliance)
    """
    # TODO: Replace with actual orchestrator call
    from src.orchestration import run_query
    result = run_query(query)

    return (
        result.value,              # float: calculated value
        result.confidence,         # float: 0-1 confidence score
        result.execution_time,     # float: seconds
        result.vee_executed,       # bool: was VEE sandbox used?
        result.source_verified,    # bool: value from VEE (not hallucinated)?
        result.temporal_compliant  # bool: no future data used?
    )

# Run validation (all queries)
report = validator.run_validation(query_executor_func=my_orchestrator)

# Print results
validator.print_report(report)
```

### 2. Category-Specific Validation

```python
# Test only Sharpe ratio queries
report = validator.run_validation(
    query_executor_func=my_orchestrator,
    category_filter="sharpe_ratio"
)

# Test first 5 queries (for quick checks)
report = validator.run_validation(
    query_executor_func=my_orchestrator,
    limit=5
)
```

### 3. Save Report to File

```python
# Save JSON report
validator.save_report(report, "reports/golden_set_2026-02-08.json")
```

---

## Understanding Results

### Validation Report Structure

```python
@dataclass
class GoldenSetReport:
    total_queries: int            # Total queries tested
    passed: int                   # Queries within tolerance
    failed: int                   # Out of tolerance or violations
    errors: int                   # Execution errors
    accuracy: float               # passed / total (should be ≥ 0.90)
    hallucination_count: int      # Queries where source_verified=False
    hallucination_rate: float     # hallucination_count / total (must be 0.0)
    temporal_violations: int      # Queries with look-ahead bias
    avg_absolute_error: float     # Mean |actual - expected|
    avg_relative_error: float     # Mean |(actual - expected) / expected|
    avg_confidence: float         # Mean confidence score
    avg_execution_time: float     # Mean execution time (seconds)
    results_by_category: Dict     # Per-category breakdown
    failed_queries: List[Dict]    # Details of failed queries
    timestamp: str                # ISO 8601 timestamp
```

### Example Report Output

```
================================================================================
GOLDEN SET VALIDATION REPORT
================================================================================

📊 Overall Results:
  Total Queries: 30
  Passed: 28 (93.3%)
  Failed: 2
  Errors: 0

🎯 Quality Metrics:
  Accuracy: 93.3%
  Hallucination Rate: 0.00% (0 queries)
  Temporal Violations: 0
  Avg Absolute Error: 0.0234
  Avg Relative Error: 1.45%
  Avg Confidence: 0.912
  Avg Execution Time: 2.34s

📋 Results by Category:
  sharpe_ratio: 9/10 (90.0%)
  correlation: 10/10 (100.0%)
  volatility: 5/5 (100.0%)
  beta: 4/5 (80.0%)

❌ Failed Queries (2):
  [gs_001] Calculate the Sharpe ratio for SPY from 2023-01-01 to 2023-12-31
    Expected: 1.743, Actual: 1.92
    Error: OUT_OF_TOLERANCE: |1.92 - 1.743| = 0.177 > 0.15

  [gs_025] Calculate the beta of TSLA relative to SPY from 2023-01-01 to 2023-12-31
    Expected: 2.212, Actual: 2.45
    Error: OUT_OF_TOLERANCE: |2.45 - 2.212| = 0.238 > 0.15

================================================================================
```

---

## CI/CD Integration

### GitHub Actions Workflow

Add to `.github/workflows/ci-cd.yml`:

```yaml
name: Golden Set Validation

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  golden-set:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Golden Set Validation
        run: |
          pytest tests/unit/test_golden_set.py::test_golden_set_ci_cd_integration -v

      - name: Check Thresholds
        run: |
          python tests/golden_set/check_thresholds.py
```

### Pre-Deployment Gate

```python
# check_thresholds.py
import json

with open("reports/golden_set_latest.json") as f:
    report = json.load(f)

# CRITICAL: These must pass or deployment fails
assert report["accuracy"] >= 0.90, \
    f"❌ Accuracy {report['accuracy']:.1%} below 90% threshold"

assert report["hallucination_rate"] == 0.0, \
    f"❌ Hallucinations detected: {report['hallucination_count']} queries"

assert report["temporal_violations"] == 0, \
    f"❌ Temporal violations: {report['temporal_violations']} queries"

print("✅ Golden Set validation passed. Deployment authorized.")
```

---

## Extending the Golden Set

### Adding New Queries

1. **Add calculation function** to `compute_expected_values.py`:

```python
def calculate_max_drawdown(ticker: str, start_date: str, end_date: str) -> float:
    """Calculate maximum drawdown for a given period."""
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)

    cumulative = (1 + data['Close'].pct_change()).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    return round(max_drawdown, 3)
```

2. **Add queries** to generation script:

```python
# In generate_golden_set()
max_drawdown_configs = [
    ("SPY", "2023-01-01", "2023-12-31"),
    ("QQQ", "2023-01-01", "2023-12-31"),
]

for ticker, start, end in max_drawdown_configs:
    mdd = calculate_max_drawdown(ticker, start, end)

    queries.append({
        "id": f"gs_{query_id:03d}",
        "category": "max_drawdown",
        "query": f"Calculate the maximum drawdown for {ticker} from {start} to {end}",
        "expected_value": mdd,
        "tolerance": 0.05,  # ±5%
        "confidence_range": [0.85, 0.95],
        # ... metadata
    })
    query_id += 1
```

3. **Regenerate golden set**:

```bash
cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА"
python tests/golden_set/compute_expected_values.py
```

4. **Update tests**:

```python
# In test_golden_set.py
def test_golden_set_has_minimum_queries(self):
    validator = GoldenSetValidator("tests/golden_set/financial_queries_v1.json")

    # Updated minimum
    assert validator.golden_set["total_queries"] >= 35, \
        "Golden set must contain at least 35 queries"
```

---

## Regenerating Expected Values

If market data changes or you want to update the reference period:

```bash
# Regenerate with latest data
python tests/golden_set/compute_expected_values.py

# Output: tests/golden_set/financial_queries_v1.json
```

**⚠️ Warning:** Regenerating will change expected values. Ensure:
1. You have a good reason (e.g., data correction, period update)
2. You commit the old version first for comparison
3. You re-validate the entire system against the new golden set

---

## Troubleshooting

### Issue: High Failure Rate

**Symptoms:** Accuracy < 90%

**Possible Causes:**
1. **Data Source Mismatch:** APE using different data provider than yfinance
2. **Calculation Differences:** Different risk-free rate, annualization method
3. **Temporal Issues:** Using updated data instead of historical snapshots

**Solutions:**
- Verify APE data sources match golden set (yfinance)
- Check calculation methods align (252 trading days/year)
- Ensure temporal cutoff dates are respected

### Issue: Hallucinations Detected

**Symptoms:** `hallucination_count > 0`

**Possible Causes:**
1. LLM generating numbers without VEE execution
2. `source_verified` flag not properly set
3. Caching returning non-VEE values

**Solutions:**
- Audit orchestrator: ensure all numeric outputs come from VEE
- Add logging to track value provenance
- Clear caches and re-test

### Issue: Temporal Violations

**Symptoms:** `temporal_violations > 0`

**Possible Causes:**
1. Using forward-looking data (future information)
2. Data leakage in training/fine-tuning
3. Incorrect date filtering in queries

**Solutions:**
- Verify all data access respects `data_cutoff` date
- Check no "future" features in model inputs
- Audit timestamp handling in data pipeline

---

## Best Practices

### 1. Version Control

```bash
# Tag golden set versions
git tag -a golden-set-v1.0 -m "Initial 30-query golden set"
git push origin golden-set-v1.0
```

### 2. Regular Validation

Run golden set validation:
- **Daily:** In CI/CD on main branch
- **Weekly:** Full report review by team
- **Pre-Release:** Mandatory gate for production deployments

### 3. Monitoring in Production

```python
# Log golden set results to monitoring
import structlog

logger = structlog.get_logger()

logger.info("golden_set_validation",
    accuracy=report.accuracy,
    hallucination_rate=report.hallucination_rate,
    avg_error=report.avg_absolute_error
)
```

### 4. Alerting

Set up alerts for:
- Accuracy drops below 90%
- Any hallucinations detected (hallucination_rate > 0)
- Temporal violations > 0
- Average error exceeds historical baseline

---

## Related Documentation

- [TESTING_COVERAGE.md](../../docs/TESTING_COVERAGE.md) - Overall test coverage
- [TECHNICAL_SPEC.md](../../docs/TECHNICAL_SPEC.md) - Week 9 Production Readiness
- [src/validation/golden_set.py](../../src/validation/golden_set.py) - Validator source code
- [tests/unit/test_golden_set.py](../../tests/unit/test_golden_set.py) - Test suite

---

## Changelog

### v1.0 (2026-02-08)
- ✅ Initial release with 30 queries
- ✅ 4 categories: Sharpe ratio, correlation, volatility, beta
- ✅ yfinance Ticker API for reliable data access
- ✅ Full CI/CD integration support
- ✅ 16 comprehensive unit tests (100% passing)

---

**Maintained by:** APE 2026 Team
**Last Updated:** 2026-02-08
**Status:** Production Ready ✅
