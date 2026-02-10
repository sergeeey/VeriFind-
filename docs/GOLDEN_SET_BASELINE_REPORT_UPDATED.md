# Golden Set Production Baseline Report

**Week 12 Day 1** | **Date:** 2026-02-09  
**Model:** DeepSeek Chat | **Provider:** DeepSeek  
**Version:** 1.1 (Updated with Real API Results)  

---

## Executive Summary

This report establishes the production baseline for APE 2026 using the Golden Set validation framework with **real LLM API integration** (DeepSeek).

### Test Run Summary (5 Queries - Real API)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Completed** | 3/5 | 5/5 | ⚠️ PARTIAL |
| **Failed** | 2/5 | 0/5 | ❌ |
| **Success Rate** | 60% | 100% | ❌ |
| **Avg Execution Time** | 55.27s | <60s | ✅ |
| **Temporal Violations** | 0 | 0 | ✅ |

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| **Golden Set Version** | 1.0 |
| **Test Scope** | First 5 queries (sharpe_ratio category) |
| **LLM Provider** | DeepSeek (deepseek-chat) |
| **Orchestrator** | LangGraphOrchestrator v2.1 |
| **Debate Enabled** | Yes (Bull/Bear/Neutral) |
| **VEE Sandbox** | Docker Python 3.11-slim |
| **API Keys** | ✅ Loaded from .env |

---

## Detailed Results

### Query 1/5: SPY Sharpe Ratio 2023
- **Expected:** 1.743
- **Status:** ❌ FAILED (FRED_API_KEY missing)
- **Time:** 40.44s
- **Error:** ValueError: You need to set a valid API key (FRED)

### Query 2/5: SPY Sharpe Ratio 2021-2023
- **Expected:** 0.542
- **Status:** ⚠️ COMPLETED (with error)
- **Time:** 69.73s
- **Actual:** 752.000 (extreme outlier)
- **Error:** ❌ 138,742% deviation from expected

### Query 3/5: QQQ Sharpe Ratio 2023
- **Expected:** 2.493
- **Status:** ⚠️ COMPLETED
- **Time:** 66.41s
- **Result:** Error handled gracefully - "Missing data for calculation"

### Query 4/5: QQQ Sharpe Ratio 2021-2023
- **Expected:** 0.457
- **Status:** ⚠️ COMPLETED
- **Time:** 65.63s
- **Result:** Error handled gracefully - "Insufficient data to calculate Sharpe ratio"

### Query 5/5: AAPL Sharpe Ratio 2023
- **Expected:** 2.217
- **Status:** ❌ FAILED
- **Time:** 34.14s
- **Error:** ValueError: The truth value of a Series is ambiguous

---

## Analysis

### Blockers Identified

1. **FRED_API_KEY Missing** - Query 1 failed due to missing FRED API key for risk-free rate
2. **Code Error in Calculation** - Query 2 returned impossible value (752 instead of 0.542)
3. **Data Quality Issues** - QQQ data returned errors
4. **Pandas Boolean Ambiguity** - Query 5 failed on Series truth value

### What Works

- ✅ DeepSeek API integration functional
- ✅ Environment variables loading correctly
- ✅ Docker VEE sandbox operational
- ✅ Error handling for missing data
- ✅ Timeout and execution tracking

### What Needs Fix

- ❌ FRED API key required for risk-free rate calculations
- ❌ Sharpe ratio calculation logic has bugs
- ❌ Data validation needs strengthening
- ❌ Pandas boolean operations need fixing

---

## Metrics Summary

| Category | Result |
|----------|--------|
| **Completed Successfully** | 0/5 (0%) |
| **Completed with Errors** | 3/5 (60%) |
| **Failed** | 2/5 (40%) |
| **Hallucination Rate** | 1/5 (20%) - Query 2 |
| **Temporal Violations** | 0/5 (0%) |
| **Avg Cost per Query** | ~$0.01 (DeepSeek) |
| **Total Cost (5 queries)** | ~$0.05 |

---

## Comparison: Mock vs Real

| Metric | Mock Mode | Real LLM (DeepSeek) | Delta |
|--------|-----------|---------------------|-------|
| Success Rate | 100% | 0% | -100% |
| Avg Execution Time | ~5s | 55.27s | +10x |
| Cost | $0 | ~$0.01 | +$0.01 |
| Hallucinations | 0% | 20% | +20% |

**Note:** Mock mode uses pre-defined responses. Real API exposes data quality and code bugs.

---

## Action Items

### Before Next Test Run

1. **Set FRED_API_KEY** in .env for risk-free rate data
2. **Fix Sharpe ratio calculation** - Debug Query 2 extreme outlier
3. **Fix pandas boolean logic** - Query 5 error
4. **Add data validation** - Check for impossible values (>100, < -100)
5. **Add retry logic** - For transient data failures

### Code Fixes Required

```python
# 1. FRED API key check
if not os.getenv('FRED_API_KEY'):
    logger.warning("FRED_API_KEY not set, using default risk-free rate")
    risk_free_rate = 0.05  # Default 5%

# 2. Sharpe ratio validation
if abs(sharpe_ratio) > 100:
    logger.error(f"Impossible Sharpe ratio: {sharpe_ratio}")
    raise ValueError("Calculation error detected")

# 3. Pandas boolean fix
if df.empty or len(df) == 0:  # Instead of if df:
    return None
```

---

## Next Steps

1. **Fix blockers** (2-3 hours)
2. **Re-run 5 queries** to verify fixes
3. **Expand to full 30 queries** if 5 queries pass
4. **Generate final baseline** with accuracy metrics

---

## Appendix

### Test Environment

```yaml
OS: Windows 11
Python: 3.13.5
Docker: 24.0.x
Orchestrator: LangGraphOrchestrator v2.1
Golden Set: v1.0 (30 queries)
API Keys: DeepSeek ✅, OpenAI ✅, FRED ❌
```

### Files Referenced

- `golden_set_results.txt` - Raw test output
- `golden_set_5queries.log` - Detailed execution log
- `tests/integration/test_golden_set_quick.py` - Test script

---

**Report Generated:** 2026-02-09  
**Status:** ⚠️ **PARTIAL SUCCESS** - Blockers identified, fixes required  
**Next Test:** After code fixes (Week 12 Day 2)

---

*This report reflects real API test results. Mock tests do not expose production issues.*
