# Wave 2 Implementation Plan

**Date:** 2026-02-11
**Duration:** 39h (estimate)
**Goal:** Commercial Value Features - Monetization & User Experience

---

## Overview

Wave 2 focuses on features that increase commercial value and user engagement:
- Standalone Debate functionality (API)
- Transparency into verification scores
- Multi-ticker comparative analysis
- Calibration system for accuracy tracking

**Dependencies:** Wave 1 MUST be complete (Neo4j, Audit, History all operational)

---

## Features (4 Total)

### 1. Standalone Debate Endpoint (4h) - P1

**Priority:** HIGH
**Effort:** 4h
**Commercial Value:** HIGH

#### What It Does
Expose the existing debate system as a standalone API endpoint, allowing users to:
- Run debate-only on any claim/question
- Get Bull/Bear/Quant perspectives without full pipeline
- Use for educational purposes or "what-if" analysis

#### Implementation

**New Files:**
- `src/api/routes/debate.py` (80 LOC)
- `tests/unit/test_debate_api.py` (4 tests)

**Endpoint:**
```python
POST /api/debate/run
{
  "claim": "AAPL will rise 10% next quarter",
  "context": {
    "ticker": "AAPL",
    "current_price": 180.5,
    "timeframe": "Q1 2026"
  },
  "agents": ["bull", "bear", "quant"],  # Optional, defaults to all 3
  "rounds": 1  # Optional, defaults to 1
}

Response:
{
  "debate_id": "debate_abc123",
  "claim": "...",
  "perspectives": {
    "bull": {"argument": "...", "confidence": 0.75, "key_points": [...]},
    "bear": {"argument": "...", "confidence": 0.60, "key_points": [...]},
    "quant": {"argument": "...", "confidence": 0.50, "key_points": [...]}
  },
  "synthesis": {
    "consensus": "...",
    "confidence_after_debate": 0.62,
    "vote_entropy": 0.83,
    "risks": [...],
    "opportunities": [...]
  },
  "cost": {
    "total_usd": 0.0024,
    "by_provider": {"deepseek": 0.0024}
  }
}
```

**Integration:**
- Reuses existing `LLMDebateNode` from orchestrator
- Bypasses PLAN/VEE/GATE — debate only
- Still tracks cost via `CostTrackingMiddleware`
- Results stored in Neo4j as Synthesis node (no VerifiedFact)

**Tests:**
- test_debate_run_success
- test_debate_run_with_context
- test_debate_run_custom_agents
- test_debate_run_cost_tracking

**Acceptance Criteria:**
- [ ] POST /api/debate/run returns valid response
- [ ] Bull/Bear/Quant perspectives generated
- [ ] Synthesis includes confidence_after_debate
- [ ] Cost tracked and returned
- [ ] 4/4 tests passing

**Time Estimate:** 4h
- 2h: API route + schema
- 1h: Tests
- 1h: Documentation + integration

---

### 2. Verification Score Transparency (6h) - P1

**Priority:** HIGH
**Effort:** 6h
**Commercial Value:** MEDIUM

#### What It Does
Expose the internal scoring mechanism used by Truth Boundary Gate:
- Show users HOW confidence scores are computed
- Break down: temporal_score × source_reliability × code_safety × numerical_match
- Educational: helps users understand why certain facts get low/high confidence

#### Implementation

**Modified Files:**
- `src/truth_boundary/gate.py` - Add `get_score_breakdown()` method
- `src/api/routes/audit.py` - Add `/api/audit/{query_id}/verification` endpoint

**New Endpoint:**
```python
GET /api/audit/{query_id}/verification

Response:
{
  "query_id": "...",
  "verified_fact_id": "fact_abc123",
  "overall_confidence": 0.85,
  "score_breakdown": {
    "temporal_score": {
      "value": 0.95,
      "weight": 0.25,
      "explanation": "Data freshness: 2 hours old, publication lag: 15 min"
    },
    "source_reliability": {
      "value": 1.0,
      "weight": 0.30,
      "explanation": "YFinance (tier 1), no fallback used"
    },
    "code_safety": {
      "value": 0.90,
      "weight": 0.20,
      "explanation": "No eval/exec, network whitelist OK, timeout OK"
    },
    "numerical_match": {
      "value": 0.80,
      "weight": 0.25,
      "explanation": "3 numbers extracted, 3 verified (100% match)"
    }
  },
  "penalties_applied": [
    {
      "type": "sensitivity",
      "amount": -0.10,
      "reason": "Sign flip detected in 20% of parameter variations"
    }
  ],
  "raw_score": 0.95,
  "final_score": 0.85,
  "grade": "HIGH_CONFIDENCE"
}
```

**Integration:**
- Truth Boundary Gate already computes these scores internally
- Need to capture and store breakdown in VerifiedFact metadata
- Expose via Audit API

**Tests:**
- test_get_verification_transparency_success
- test_get_verification_transparency_with_penalties
- test_get_verification_transparency_low_score
- test_get_verification_transparency_not_found

**Acceptance Criteria:**
- [ ] GET /api/audit/{query_id}/verification returns breakdown
- [ ] All 4 score components present
- [ ] Penalties listed if applicable
- [ ] Human-readable explanations for each score
- [ ] 4/4 tests passing

**Time Estimate:** 6h
- 3h: Modify gate.py to capture score breakdown
- 2h: API endpoint + schema
- 1h: Tests + documentation

---

### 3. Multi-Ticker Comparative Analysis (8h) - P1

**Priority:** MEDIUM
**Effort:** 8h
**Commercial Value:** HIGH

#### What It Does
Allow users to compare multiple tickers side-by-side:
- Run analysis for 2-10 tickers simultaneously
- Return comparative metrics (correlation, relative strength, sector trends)
- Useful for portfolio construction and sector rotation strategies

#### Implementation

**New Files:**
- `src/api/routes/compare.py` (120 LOC)
- `src/analysis/comparative_metrics.py` (150 LOC)
- `tests/unit/test_compare_api.py` (5 tests)

**Endpoint:**
```python
POST /api/compare/tickers
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "metrics": ["price_momentum", "correlation", "sharpe_ratio", "volatility"],
  "timeframe": "1y",
  "benchmark": "SPY"  # Optional
}

Response:
{
  "comparison_id": "cmp_abc123",
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "timeframe": "1y",
  "analysis": {
    "AAPL": {
      "price_momentum": {"1m": 0.05, "3m": 0.12, "1y": 0.28},
      "sharpe_ratio": 1.2,
      "volatility": 0.22,
      "correlation_to_benchmark": 0.85
    },
    "MSFT": {...},
    "GOOGL": {...}
  },
  "comparative_insights": {
    "correlation_matrix": [[1.0, 0.75, 0.68], [0.75, 1.0, 0.72], [0.68, 0.72, 1.0]],
    "strongest_correlation": {"pair": ["AAPL", "MSFT"], "value": 0.75},
    "weakest_correlation": {"pair": ["AAPL", "GOOGL"], "value": 0.68},
    "volatility_ranking": ["GOOGL", "AAPL", "MSFT"],
    "momentum_ranking": ["MSFT", "AAPL", "GOOGL"]
  },
  "verified_fact": {
    "fact_id": "fact_cmp_abc123",
    "statement": "Comparative analysis computed via deterministic execution",
    "confidence_score": 0.95,
    "data_source": "yfinance"
  }
}
```

**Integration:**
- Uses existing yfinance adapter
- Reuses PortfolioOptimizer correlation logic
- Bypasses LLM — pure mathematical comparison
- Results stored in Neo4j as VerifiedFact

**Tests:**
- test_compare_tickers_success
- test_compare_tickers_correlation_matrix
- test_compare_tickers_with_benchmark
- test_compare_tickers_invalid_ticker
- test_compare_tickers_empty_data

**Acceptance Criteria:**
- [ ] POST /api/compare/tickers returns comparative analysis
- [ ] Correlation matrix computed correctly
- [ ] Momentum/volatility rankings accurate
- [ ] Works with 2-10 tickers
- [ ] 5/5 tests passing

**Time Estimate:** 8h
- 4h: comparative_metrics.py implementation
- 2h: API route + schema
- 2h: Tests + documentation

---

### 4. Calibration Training Pipeline (6h) - P2

**Priority:** MEDIUM
**Effort:** 6h
**Commercial Value:** MEDIUM

#### What It Does
Automated system to track prediction accuracy over time and calibrate confidence scores:
- Evaluate predictions when target_date reached
- Compute calibration error (predicted confidence vs actual accuracy)
- Store calibration data for model improvement

#### Implementation

**New Files:**
- `src/predictions/calibration.py` (180 LOC)
- `tests/unit/test_calibration.py` (6 tests)

**Modules:**
```python
class CalibrationTracker:
    def compute_calibration_curve(self, predictions: List[Prediction]):
        """
        Compute calibration curve (Expected Calibration Error).

        Groups predictions by confidence bins (0-0.1, 0.1-0.2, etc.)
        Compares predicted confidence to actual accuracy in each bin.
        """

    def compute_brier_score(self, predictions: List[Prediction]):
        """
        Brier score: (confidence - actual)^2
        Lower is better. Perfect score = 0.
        """

    def recommend_adjustments(self, calibration_data):
        """
        Recommend confidence score adjustments.
        E.g., "Model is overconfident in 0.7-0.8 range by 15%"
        """
```

**Integration:**
- Extends existing `AccuracyTracker` from predictions/accuracy_tracker.py
- Uses `PredictionScheduler` to run daily
- Stores calibration data in TimescaleDB
- API endpoint: GET /api/predictions/calibration

**API Endpoint:**
```python
GET /api/predictions/calibration?days=30

Response:
{
  "calibration_period": "30 days",
  "total_evaluated": 150,
  "expected_calibration_error": 0.08,  # Lower is better, <0.05 is good
  "brier_score": 0.12,
  "calibration_curve": [
    {"confidence_bin": "0.0-0.1", "predicted_prob": 0.05, "actual_accuracy": 0.02, "count": 10},
    {"confidence_bin": "0.1-0.2", "predicted_prob": 0.15, "actual_accuracy": 0.18, "count": 15},
    ...
  ],
  "recommendations": [
    {
      "bin": "0.7-0.8",
      "issue": "overconfident",
      "adjustment": -0.12,
      "message": "Model overestimates accuracy by 12% in this range"
    }
  ]
}
```

**Tests:**
- test_compute_calibration_curve
- test_compute_brier_score
- test_recommend_adjustments
- test_calibration_api_endpoint
- test_calibration_with_no_data
- test_calibration_integration_with_scheduler

**Acceptance Criteria:**
- [ ] Calibration curve computed correctly (ECE < 0.10)
- [ ] Brier score calculated
- [ ] Recommendations generated
- [ ] GET /api/predictions/calibration works
- [ ] Integration with PredictionScheduler
- [ ] 6/6 tests passing

**Time Estimate:** 6h
- 3h: calibration.py implementation (ECE, Brier score, recommendations)
- 1h: API endpoint
- 2h: Tests + integration

---

## Dependencies

```
Wave 1 (MUST BE COMPLETE):
├── Neo4j Integration ✅
├── Audit Trail API ✅
├── Query History ✅
├── Prediction Scheduler ✅
└── Portfolio API ✅

Wave 2:
├── Feature 1: Standalone Debate
│   └── Depends on: LLMDebateNode (exists)
├── Feature 2: Verification Transparency
│   └── Depends on: Truth Boundary Gate (exists), Audit API (exists)
├── Feature 3: Multi-Ticker Compare
│   └── Depends on: yfinance adapter (exists), PortfolioOptimizer (exists)
└── Feature 4: Calibration Pipeline
    └── Depends on: PredictionScheduler (Wave 1 ✅), AccuracyTracker (exists)
```

**No blocking dependencies** - all Wave 2 features can proceed in parallel.

---

## Implementation Order

### Week 1 (Day 1-2): Standalone Debate
- **Day 1:** API route + schema (2h)
- **Day 2:** Tests + documentation (2h)

### Week 1 (Day 3-4): Verification Transparency
- **Day 3:** Modify gate.py, API endpoint (4h)
- **Day 4:** Tests + documentation (2h)

### Week 2 (Day 1-3): Multi-Ticker Compare
- **Day 1:** comparative_metrics.py (4h)
- **Day 2:** API route + tests (3h)
- **Day 3:** Documentation + integration (1h)

### Week 2 (Day 4-5): Calibration Pipeline
- **Day 4:** calibration.py + API (4h)
- **Day 5:** Tests + integration (2h)

**Total:** 24h actual work (39h with buffer for debugging/testing)

---

## Testing Strategy

### Unit Tests (21 new tests)
- test_debate_api.py: 4 tests
- test_compare_api.py: 5 tests
- test_calibration.py: 6 tests
- test_verification_transparency.py: 4 tests
- test_comparative_metrics.py: 2 tests

### Integration Tests (4 new tests)
- test_debate_end_to_end.py
- test_compare_with_real_data.py
- test_calibration_with_scheduler.py
- test_verification_with_pipeline.py

**Target Coverage:** 95% for new code

---

## Acceptance Criteria (Wave 2)

| Criterion | Target | Validation |
|-----------|--------|------------|
| All 4 features implemented | 100% | Code review |
| All 25 tests passing | 100% | pytest |
| API documentation complete | 100% | Swagger/OpenAPI |
| No regressions in Wave 1 | 100% | Regression tests |
| Code coverage (new) | ≥95% | pytest --cov |
| Performance (new endpoints) | <2s | Load testing |

---

## Known Risks

### Risk 1: Debate API Cost
**Issue:** Standalone debate might be expensive if users spam it
**Mitigation:**
- Rate limiting (10 requests/hour per user)
- Cost tracking + warnings
- Consider: paid tier only

### Risk 2: Multi-Ticker Data Volume
**Issue:** 10 tickers × 1 year data = large payload
**Mitigation:**
- Limit to 10 tickers max
- Cache results (1 hour TTL)
- Paginate if needed

### Risk 3: Calibration Data Sparsity
**Issue:** Need sufficient predictions to compute calibration (min 30-50)
**Mitigation:**
- Return 404 if < 30 predictions
- Show "Not enough data" message
- Populate with historical predictions

---

## Documentation

### Files to Create
1. `docs/api/DEBATE_API.md` - Standalone debate endpoint
2. `docs/api/COMPARE_API.md` - Multi-ticker comparison
3. `docs/api/CALIBRATION_API.md` - Calibration system
4. `docs/VERIFICATION_TRANSPARENCY.md` - Score breakdown explanation

### Files to Update
1. `docs/API.md` - Add new endpoints
2. `README.md` - Update features list
3. `.memory_bank/progress.md` - Track Wave 2 progress
4. `.memory_bank/tech-spec.md` - New technical specs

---

## Commit Strategy

### Commits (4 total)
1. `feat(wave2): Standalone Debate endpoint + tests`
2. `feat(wave2): Verification Score Transparency`
3. `feat(wave2): Multi-Ticker Comparative Analysis`
4. `feat(wave2): Calibration Training Pipeline`

**Final Commit:**
```
feat(wave2): Complete Wave 2 implementation - Debate, Verification, Compare, Calibration

## Summary
Implemented all 4 Wave 2 commercial value features:
- Standalone Debate API (4h)
- Verification Score Transparency (6h)
- Multi-Ticker Comparative Analysis (8h)
- Calibration Training Pipeline (6h)

## Stats
- New Files: 8
- Modified Files: 10+
- New Code: ~530 LOC
- New Tests: 25 (21 unit + 4 integration)
- Tests Passing: 25/25 (100%)

## API Endpoints
- POST /api/debate/run
- GET /api/audit/{query_id}/verification
- POST /api/compare/tickers
- GET /api/predictions/calibration

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Success Metrics

**Wave 2 Complete When:**
- ✅ All 4 features implemented
- ✅ 25/25 new tests passing
- ✅ No Wave 1 regressions
- ✅ Documentation complete
- ✅ Code coverage ≥95%
- ✅ Performance < 2s per endpoint

**Grade Target:** A (9.0/10)

---

**Ready to start implementation!**

**First Task:** Feature 1 - Standalone Debate Endpoint (4h)

**Delegation:** Can be split across multiple agents if needed
- Agent 1: Standalone Debate (4h)
- Agent 2: Verification Transparency (6h)
- Agent 3: Multi-Ticker Compare (8h)
- Agent 4: Calibration Pipeline (6h)

**Total Wave 2:** 24h implementation + 15h buffer = 39h
