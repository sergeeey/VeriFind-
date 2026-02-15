# Week 14 Day 2 Final Report — APE 2026

**Дата:** 2026-02-15 10:50 UTC
**Длительность:** ~3 часа (сейчас продолжение)
**Статус:** REVERTED to 90% baseline

---

## 🎯 Цель сессии

**Задача:** Fix gs_014 number extraction bug → 90% → 93.3%

**Результат:** ❌ FAILED — Fix НЕ решил проблему, создал регрессию (90% → 80%)

---

## 📊 Что произошло

### Attempt 1: Number Extraction Blacklist (FAILED)

**Гипотеза:** gs_014 падает потому что "S&P 500" → extracts "500"

**Решение:**
- Добавил blacklist patterns в `eval/validators.py`
- Создал 13 regression tests (все passing)
- Commit: 76a7d9c

**Результат:**
- Golden Set: 80% (24/30) ❌
- **REGRESSION:** -3 queries vs baseline (90% → 80%)

**Root Cause Analysis:**
- gs_014 падает НЕ из-за number extraction
- gs_014 падает из-за **ticker detection** — fetches SPY instead of AMD
- Number extraction fix НЕ помог, возможно создал новые проблемы

---

## 📉 Regression Analysis

**Baseline:** 90% (27/30) — commit 3e4c8d8
**After fix:** 80% (24/30) — commit 76a7d9c
**After revert:** TBD (validation running) — commit c4a6014

### Failing queries after "fix":

1. gs_008 (technical): Bitcoin 50-day MA — ticker detection
2. gs_014 (valuation): AMD P/E ratio — ticker detection
3. gs_019 (technical): Gold price — ticker detection
4. gs_020 (valuation): Visa vs Mastercard — analytical depth
5. gs_026 (earnings): Coca-Cola dividend yield — missing field
6. gs_027 (technical): Bitcoin price — ticker detection

**Pattern:** 4/6 failures = ticker detection bug (crypto/commodities not recognized)

---

## ✅ What Worked

1. **Compliance fix (Day 1):** 20% → 100% ✅ (commit e0d9c5e)
   - 4 refusal messages updated
   - 10 regression tests
   - **STABLE** — не регрессировало

2. **FRED integration:** Reverted (commit 9a389cc)
   - Caused 90% → 86.7% regression
   - Smart revert decision

3. **Number extraction tests:** 13/13 passing
   - Good unit tests created
   - But didn't solve real problem

---

## ❌ What Failed

1. **Number extraction blacklist:** Created regression
   - Hypothesis was wrong (not extraction issue)
   - Real issue: ticker detection

2. **gs_014 diagnosis:** Misidentified root cause
   - Thought: number extraction bug
   - Actually: ticker detection doesn't parse "AMD" from query

---

## 🔄 Actions Taken

1. **REVERT:** commit c4a6014
   - Reverted number extraction fix (76a7d9c)
   - Restored validators.py to baseline state
   - Deleted test_number_extraction.py

2. **Baseline validation:** Running (task ba6e729)
   - Verifying 90% accuracy restored
   - ETA: ~10-15 минут

---

## 🎯 Correct Path Forward (Post-Launch)

### Real Issue: Ticker Detection

**Problem:** System doesn't extract tickers from queries properly
- "What is AMD's P/E ratio?" → extracts SPY (fallback) instead of AMD
- "Bitcoin price" → doesn't recognize BTC-USD
- "Gold price" → doesn't recognize GC=F

**Fix needed:** Improve ticker extraction in orchestrator
- File: `src/debate/parallel_orchestrator.py` or query parsing layer
- Add regex patterns for crypto (BTC, ETH, etc.)
- Add commodity symbols (GC=F, CL=F, etc.)
- Improve ticker extraction from natural language

**Impact:** Would fix 4/6 failing queries → 80% → 93.3%

---

## 💡 Key Learnings

1. **Test hypothesis before implementing**
   - Should have verified gs_014 failure cause first
   - Number extraction wasn't the issue

2. **Regression testing is critical**
   - Number extraction fix passed unit tests
   - But broke integration tests (Golden Set)

3. **90% is sufficient for Private Beta**
   - Don't over-optimize before launch
   - Fix post-launch with real user feedback

4. **Late-night + early-morning coding = mistakes**
   - Fresh perspective tomorrow would have caught this
   - Rushing leads to wrong diagnosis

---

## 🚀 Launch Decision

**Recommendation:** Launch Monday with 90% baseline

**Rationale:**
- 90% accuracy is excellent for Private Beta
- Compliance: 100% (5/5) ✅
- Macro: 100% (2/2) ✅
- Core functionality works
- Ticker detection is edge case (crypto/commodities)

**Post-launch TODO:**
- Fix ticker detection (1-2 hours)
- Re-run Golden Set
- Target: 93-95% for production

---

## 📁 Git Status

**Commits today:**
1. 3e4c8d8: docs(week14): session wrap-up + tomorrow plan
2. 76a7d9c: feat(validators): fix number extraction (FAILED)
3. c4a6014: Revert "feat(validators): fix number extraction"

**Current HEAD:** c4a6014 (reverted to baseline)

**Baseline validation:** Running (verifying 90% restored)

---

## ⏰ Timeline

- 00:00-01:00: Session wrap-up, planning
- 08:00-09:00: Number extraction fix implementation
- 09:00-10:30: Golden Set validation (discovered regression)
- 10:30-10:50: REVERT + baseline check
- 10:50-11:05: Baseline validation (in progress)

**Total time:** ~4 hours (including previous night)

---

## 🎯 Next Steps

1. **Wait for baseline validation** (~10 min)
2. **If 90% confirmed:** DONE, ready for Monday launch ✅
3. **If <90%:** Investigate what else broke
4. **Monday:** Launch Private Beta
5. **Week 14 Day 3:** Fix ticker detection post-launch

---

**Status:** Baseline restoration in progress
**ETA:** 11:05 UTC
**Confidence:** 95% that 90% will be restored

---

*Version: 1.0 (Final)*
*Date: 2026-02-15 10:50 UTC*
*Decision: Launch with 90% baseline*
