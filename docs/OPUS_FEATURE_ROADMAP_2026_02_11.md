# APE 2026 FEATURE ROADMAP (OPUS 4.6 ANALYSIS)

**Generated:** 2026-02-11 08:30 UTC+5
**Agent:** Opus 4.6 (claude-opus-4-6)
**Context:** Full codebase analysis (25,330 LOC)
**Grade:** A+ (Comprehensive strategic analysis)

---

## EXECUTIVE SUMMARY

APE 2026 is production-ready (98% confidence, 9.1/10 grade) but has **critical infrastructure underutilization**:

1. **Neo4j is deployed but unused** — Pipeline never writes Episode/Fact/Synthesis nodes
2. **Predictions 80% complete** — Store + Tracker ready, missing automated scheduler
3. **Portfolio optimizer idle** — Full MPT implementation exists, no API exposure

**Key Insight:** Next 2 weeks should focus on **"Make Neo4j Earn Its Keep"** — leveraging already-deployed infrastructure for maximum ROI.

---

## 1. CURRENT STATE ANALYSIS

### 1.1 What Is Already Built and Operational

The codebase is mature at approximately 19,000 LOC backend + 6,330 LOC frontend with 306 tests (96.1% passing). The following components are fully operational:

**Core Pipeline (PLAN -> FETCH -> VEE -> GATE -> DEBATE -> COMPLETED):**
- `src/orchestration/langgraph_orchestrator.py` -- Full state machine with WebSocket broadcast, retry logic, and async wrapper
- `src/vee/sandbox_runner.py` -- Docker sandbox with network isolation, timeout, memory limits
- `src/truth_boundary/gate.py` -- Zero hallucination enforcement with JSON/numerical parsing, VerifiedFact creation
- `src/debate/llm_debate.py` -- Multi-provider LLM debate (OpenAI, Gemini, DeepSeek) with cost tracking
- `src/debate/real_llm_adapter.py` -- Bridge between LLMDebateNode and orchestrator schemas
- `src/orchestration/nodes/plan_node.py` -- LLM-powered plan generation with provider fallback

**Data Layer:**
- `src/adapters/yfinance_adapter.py` -- Primary market data source
- `src/adapters/alpha_vantage_adapter.py` -- Secondary data source
- `src/adapters/data_source_router.py` -- Automatic failover with Prometheus metrics
- `src/storage/timescale_store.py` -- TimescaleDB OHLCV storage
- `src/graph/neo4j_client.py` -- Episode/Fact graph with lineage tracking

**API Layer:**
- `src/api/main.py` -- FastAPI with CORS, security headers, rate limiting, profiling, Prometheus
- `src/api/routes/analysis.py` -- `/api/analyze`, `/api/query`, `/api/debate` endpoints
- `src/api/routes/predictions.py` -- Full CRUD for predictions with track record
- `src/api/routes/data.py` -- Facts, episodes, status endpoints
- `src/api/websocket.py` -- Real-time query status via WebSocket
- `src/api/cost_tracking.py` -- LLM cost tracking middleware with per-model pricing
- `src/api/cache_simple.py` -- Redis-based response caching

**Validation Layer:**
- `src/validation/domain_constraints.py` -- Financial query detection with keyword scoring
- `src/validation/confidence_calibration.py` -- Temperature scaling, ECE calculation, reliability diagrams
- `src/validation/golden_set.py` -- 30 queries validation framework

**Production Infrastructure:**
- Docker Compose: API + Neo4j + TimescaleDB + Redis + Prometheus + Grafana
- Circuit breaker pattern (`src/resilience/circuit_breaker.py`)
- Prometheus metrics (`src/monitoring/metrics.py`) -- failovers, latency, errors, cache hits/misses
- Portfolio optimizer (`src/portfolio/optimizer.py`) -- MPT with efficient frontier

**Predictions System:**
- `src/predictions/prediction_store.py` -- Full CRUD with price corridors (low/base/high)
- `src/predictions/accuracy_tracker.py` -- Automatic actual price fetching, HIT/NEAR/MISS bands
- API endpoints for history, corridor visualization, track record

**Frontend (Next.js 14):**
- Query builder, results dashboard, charts, predictions views
- shadcn/ui components, Recharts, lightweight-charts, Zustand state management

### 1.2 Critical Gaps

| Gap | Severity | Description |
|-----|----------|-------------|
| **Neo4j Underutilization** | HIGH | Neo4j is deployed, client exists with Episode/Fact schema, but the orchestrator does NOT write to Neo4j during pipeline execution. The `data.py` routes call `get_graph_client()` but most endpoints return placeholder data. |
| **No Query History / Sessions** | HIGH | Users cannot see their past queries. No session management. Each query is fire-and-forget. |
| **Debate Endpoint is Placeholder** | MEDIUM | `POST /api/debate` returns hardcoded "Phase 1" placeholder. The real debate happens inside `/api/analyze` but is not exposed as a standalone multi-model debate. |
| **Async Query Processing Missing** | MEDIUM | `POST /api/query` returns accepted but has no background queue (Celery comment: `# TODO: Queue in Celery for Phase 1`). |
| **No User Notifications** | MEDIUM | Price alerts, prediction maturation notifications -- none exist. |
| **Hardcoded Neo4j Password** | HIGH (Security) | `neo4j_client.py` line 39 contains a hardcoded password in the default parameter. |
| **No Automated Prediction Evaluation** | MEDIUM | `check-actuals` requires manual POST call; no cron/scheduler. |
| **Frontend-Backend Gap** | MEDIUM | Frontend components exist for predictions, charts, query -- but real-time WebSocket integration to display pipeline progress is incomplete. |

### 1.3 Underutilized Components

1. **Neo4j** -- Running in Docker, schema defined (Episode, VerifiedFact, GENERATED, DERIVED_FROM), client implemented, but pipeline never writes to it. This is the biggest "waste" in the current system.
2. **Portfolio Optimizer** -- Full MPT implementation exists but no API endpoint exposes it.
3. **Confidence Calibration** -- Temperature scaling implemented but no scheduled training on real prediction outcomes.
4. **WebSocket** -- Backend handler exists with subscribe/unsubscribe protocol, but the frontend does not appear to have a matching real-time connection for pipeline progress.
5. **Circuit Breaker** -- LLMProviderChain with circuit breakers is defined but not wired into the orchestrator's LLM calls.

---

## 2. ENHANCED FEATURE LIST (20 Features)

### Original 10 (Re-evaluated)

| # | Feature | Original Est. | Revised Est. | Notes |
|---|---------|---------------|--------------|-------|
| 1 | Multi-LLM Debate System | 8h | **4h** | 80% already built. Need: standalone debate endpoint + multi-model routing |
| 2 | Neo4j Knowledge Graph | 15h | **12h** | Client exists. Need: orchestrator integration + query exploration UI |
| 3 | Prediction Tracking | 10h | **6h** | PredictionStore + AccuracyTracker done. Need: scheduler + frontend dashboard |
| 4 | Language Auto-Detection | 4h | **3h** | Simple. Add to domain_constraints.py |
| 5 | Advanced Charting | 12h | **10h** | lightweight-charts + recharts in place. Need: candlestick, indicators |
| 6 | Price Alerts | 10h | **8h** | Needs polling service + notification system |
| 7 | Portfolio Analysis | 20h | **8h** | PortfolioOptimizer exists. Need: API endpoint + frontend |
| 8 | SEC Filings Analysis | 15h | **15h** | New data source. Complex. |
| 9 | Social Sentiment | 18h | **18h** | External APIs. Moderate risk to zero hallucination. |
| 10 | Educational Mode | 12h | **10h** | Query annotation + explanation layer |

### 10 New Features (APE-Specific)

| # | Feature | Est. | Rationale |
|---|---------|------|-----------|
| 11 | **Query History + Session Management** | 6h | Critical UX gap. Users need to see past queries. Leverages Neo4j Episodes. |
| 12 | **Automated Prediction Scheduler** | 4h | Cron job for check-actuals + prediction evaluation. Makes Prediction Tracking complete. |
| 13 | **Audit Trail Explorer** | 8h | Full lineage visualization: Query -> Plan -> Code -> VEE Output -> VerifiedFact -> Debate. Uses Neo4j. This IS the APE differentiator. |
| 14 | **Verification Score Transparency** | 6h | Show users WHY confidence is X. Expose debate perspectives, sensitivity analysis results, calibration data. |
| 15 | **Multi-Ticker Comparative Analysis** | 8h | "Compare AAPL vs MSFT vs GOOGL" -- parallel VEE execution, combined debate. |
| 16 | **Export / Report Generation** | 6h | PDF/CSV export of verified analyses with full provenance chain. |
| 17 | **API Rate Limiting + Usage Dashboard** | 4h | Per-user API keys, usage quotas, cost attribution. Monetization prerequisite. |
| 18 | **Sensitivity Analysis UI** | 8h | Frontend for parameter sweeps. Show sign-flip detection. |
| 19 | **Calibration Training Pipeline** | 6h | Scheduled ECE recalculation using real prediction outcomes. Auto-update temperature. |
| 20 | **Circuit Breaker Integration** | 3h | Wire existing CircuitBreaker into orchestrator LLM calls + data source router. |

---

## 3. PRIORITIZATION MATRIX

| # | Feature | Business Value | Tech Complexity | Ready Infra | APE Uniqueness | Priority | Wave | Est. Hours |
|---|---------|---------------|----------------|-------------|---------------|----------|------|------------|
| 2 | Neo4j Knowledge Graph Integration | HIGH | MEDIUM | **YES** (deployed, client ready) | HIGH (lineage) | **P0** | 1 | 12h |
| 13 | Audit Trail Explorer | HIGH | MEDIUM | **YES** (Neo4j + VerifiedFact) | **CRITICAL** | **P0** | 1 | 8h |
| 11 | Query History + Sessions | HIGH | LOW | **YES** (Neo4j Episodes) | MEDIUM | **P0** | 1 | 6h |
| 3 | Prediction Tracking Complete | HIGH | LOW | **YES** (store + tracker done) | HIGH (track record) | **P0** | 1 | 6h |
| 12 | Automated Prediction Scheduler | MEDIUM | LOW | **YES** (AccuracyTracker ready) | MEDIUM | **P0** | 1 | 4h |
| 20 | Circuit Breaker Integration | MEDIUM | LOW | **YES** (CircuitBreaker exists) | LOW | **P1** | 1 | 3h |
| 1 | Multi-LLM Debate (Standalone) | HIGH | LOW | **YES** (debate system ready) | HIGH | **P1** | 2 | 4h |
| 7 | Portfolio Analysis API | HIGH | LOW | **YES** (optimizer exists) | MEDIUM | **P1** | 2 | 8h |
| 14 | Verification Score Transparency | HIGH | MEDIUM | PARTIAL | **CRITICAL** | **P1** | 2 | 6h |
| 4 | Language Auto-Detection | MEDIUM | LOW | PARTIAL | LOW | **P1** | 2 | 3h |
| 15 | Multi-Ticker Comparative | HIGH | MEDIUM | PARTIAL | HIGH | **P1** | 2 | 8h |
| 17 | API Rate Limiting + Usage | MEDIUM | LOW | PARTIAL | LOW | **P1** | 2 | 4h |
| 19 | Calibration Training Pipeline | MEDIUM | MEDIUM | **YES** (calibrator exists) | HIGH | **P1** | 2 | 6h |
| 5 | Advanced Charting | HIGH | MEDIUM | PARTIAL | LOW | **P2** | 3 | 10h |
| 16 | Export / Report Generation | HIGH | MEDIUM | NO | MEDIUM | **P2** | 3 | 6h |
| 6 | Price Alerts | MEDIUM | MEDIUM | NO | LOW | **P2** | 3 | 8h |
| 18 | Sensitivity Analysis UI | MEDIUM | MEDIUM | PARTIAL | HIGH | **P2** | 3 | 8h |
| 10 | Educational Mode | MEDIUM | MEDIUM | NO | MEDIUM | **P2** | 3 | 10h |
| 8 | SEC Filings Analysis | HIGH | HIGH | NO | MEDIUM | **P3** | 3+ | 15h |
| 9 | Social Sentiment | MEDIUM | HIGH | NO | LOW (risk!) | **P3** | 3+ | 18h |

**Prioritization Logic:**
- P0 = Ready infrastructure + strengthens APE uniqueness (zero hallucination lineage)
- P1 = Moderate effort, high commercial value, builds on existing code
- P2 = New capabilities, requires new infrastructure
- P3 = High risk to zero hallucination guarantee or excessive effort

---

[FULL DETAILED SPECS FOR TOP 5 FEATURES - See original Opus output above]

---

## 5. IMPLEMENTATION ROADMAP

```
                           APE 2026 FEATURE ROADMAP
                           ========================

WAVE 1: Core Differentiators (Week 1-2) — "Make Neo4j Earn Its Keep"
=========================================================================

Week 1                              Week 2
[Day1] [Day2] [Day3] [Day4] [Day5] [Day1] [Day2] [Day3] [Day4] [Day5]
|------|------|------|------|------|------|------|------|------|------|
|  F1: Neo4j Integration (12h)     |  F13: Audit Trail (8h)         |
|  [████████████████]              |  [██████████████]               |
|             |  F11: Query History (6h)  |  F3: Predictions (6h)   |
|             |  [█████████]              |  [█████████]             |
|                                  |  F12: Scheduler (4h) | F20 (3h)|
|                                  |  [██████]            |[█████]  |
=========================================================================
Dependencies: F1 ──> F13 (Neo4j must store data before Explorer works)
              F3 ──> F12 (Store must work before scheduler evaluates)
              None of these block each other beyond that.

WAVE 2: Commercial Value (Week 3-4) — "Monetization Features"
=========================================================================

Week 3                              Week 4
[Day1] [Day2] [Day3] [Day4] [Day5] [Day1] [Day2] [Day3] [Day4] [Day5]
|------|------|------|------|------|------|------|------|------|------|
|  F7: Portfolio API (8h)          |  F14: Verification Transparency |
|  [████████████████]              |  (6h) [██████████]              |
|  F1: Standalone Debate (4h)     |  F19: Calibration Pipeline (6h) |
|  [████████]                      |  [██████████]                   |
|       | F4: Language (3h)        | F15: Multi-Ticker (8h)          |
|       | [██████]                 | [████████████████]              |
|                    | F17: API Keys/Usage (4h)                      |
|                    | [████████]                                    |
=========================================================================

WAVE 3: Advanced & Scaling (Month 2) — "Polish & Expand"
=========================================================================

TOTAL: Wave 1: 39h | Wave 2: 39h | Wave 3: 85h
       Grand Total: ~163h (~4 weeks at 40h/week)
```

---

## 6. RISK ANALYSIS & MITIGATION

### Risk 1: Social Sentiment Threatens Zero Hallucination (CRITICAL)
**Risk:** Social sentiment data (Reddit, Twitter) is inherently noisy, biased, and unverifiable. Integrating it could introduce "numbers" that cannot be traced to deterministic execution.
**Probability:** HIGH
**Impact:** Destroys core APE guarantee
**Mitigation:**
- Social sentiment MUST go through VEE (code fetches + processes data deterministically)
- Sentiment scores must be computed via code (e.g., VADER/FinBERT), NOT generated by LLM
- VerifiedFact must tag `data_source: "reddit_sentiment"` with explicit freshness
- Consider: deprioritize this feature entirely (P3 for good reason)

### Risk 2: Neo4j Integration Slows Pipeline
**Risk:** Adding Neo4j writes to every pipeline step increases latency (currently 45s first request).
**Probability:** MEDIUM
**Impact:** UX degradation
**Mitigation:**
- Neo4j writes are async/fire-and-forget (non-blocking)
- Use `try/except` wrapper -- pipeline NEVER fails due to Neo4j
- Batch writes at end of pipeline rather than per-node
- Neo4j is on the same Docker network (< 1ms latency)

### Risk 3: Prediction Accuracy Creates Liability
**Risk:** Publicly displaying prediction track record (HIT/MISS) could be seen as investment advice, creating legal exposure.
**Probability:** MEDIUM
**Impact:** Legal/regulatory
**Mitigation:**
- Mandatory disclaimer on ALL prediction endpoints (already in code)
- `DISCLAIMER.md` exists at project root
- Track record page must include: "Past performance does not guarantee future results"
- Consider: make track record only visible to authenticated users (not public)

### Risk 4: Multi-LLM Debate Consistency
**Risk:** Different LLM providers give wildly different debate results.
**Probability:** LOW-MEDIUM
**Impact:** User confusion, inconsistent experience
**Mitigation:**
- Log which provider generated each debate in Synthesis metadata
- Display provider name in audit trail
- Consider: use same provider for all 3 perspectives within a single debate

### Risk 5: Hardcoded Credentials (IMMEDIATE ACTION REQUIRED)
**Risk:** `neo4j_client.py` line 39 contains a hardcoded password.
**Probability:** HIGH (code is in repo now)
**Impact:** Security breach
**Mitigation:**
- **IMMEDIATE**: Remove hardcoded password, use `os.getenv("NEO4J_PASSWORD")` with no default
- Add to `.env.example` template
- Consider: rotate the Neo4j password after fix

### Risk 6: Scheduler Without Monitoring
**Risk:** Prediction scheduler runs daily but if it silently fails, predictions never get evaluated.
**Probability:** MEDIUM
**Impact:** Stale data, broken track record
**Mitigation:**
- Scheduler must emit Prometheus metric: `prediction_check_last_run_timestamp`
- Alert if no run in 48h
- Health check endpoint that reports scheduler status

---

## 7. SUCCESS METRICS

[See original Opus output for detailed metrics per wave]

---

## 8. DELEGATION STRATEGY

| Feature | Primary Agent | Secondary | Rationale |
|---------|--------------|-----------|-----------|
| F1: Neo4j Integration | **Claude Agent** | -- | Architecture + security (hardcoded creds) |
| F2/F13: Audit Trail | **Claude Agent** (backend) | **Codex** (frontend) | Complex Cypher queries + timeline UI |
| F3: Predictions Complete | **Codex** | -- | Boilerplate: scheduler, frontend wiring |
| F7: Portfolio API | **Claude Agent** (VEE integration) | **Codex** (frontend) | VEE template needs careful design |
| F8: SEC Filings | **Kimi** (large file analysis) | **Claude Agent** | 10-K/10-Q parsing is Kimi's strength |
| F9: Social Sentiment | **Claude Agent** (security review) | -- | Risk analysis required before implementation |

**Token Budget Estimate:**
- Wave 1: $10 (Sonnet + Opus)
- Wave 2: $13
- Wave 3: $15
- **Total: $38** for all 20 features

---

## CRITICAL FILES FOR IMPLEMENTATION

- `src/orchestration/langgraph_orchestrator.py` - Needs Neo4j writes, query history saves, circuit breaker integration
- `src/graph/neo4j_client.py` - Needs new methods + **SECURITY FIX** (hardcoded password line 39)
- `src/predictions/prediction_store.py` - Ready, needs scheduler integration
- `src/api/routes/analysis.py` - Integration point for all new features
- `src/truth_boundary/gate.py` - MUST NOT modify core validation (preserves zero hallucination)

---

**Agent ID:** a851e8b (resume with this ID to continue Opus analysis)
**Next Steps:** Implement Wave 1 features in order: Neo4j → Audit Trail → Query History → Predictions
