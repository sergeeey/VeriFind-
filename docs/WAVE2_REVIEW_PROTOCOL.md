# Wave 2 Review Protocol

**Reviewer:** Claude Sonnet 4.5
**Role:** Quality Assurance & Integration Verification
**Implementation:** Other agent(s)

---

## Review Workflow

### When Implementation Agent Finishes a Feature:

#### Step 1: Notify Me
```
"Feature [N] completed. Ready for review."
```

#### Step 2: I Will Review
```
1. Read all new/modified files
2. Compare to specification
3. Check code quality
4. Run tests
5. Security scan
6. Regression check
```

#### Step 3: I Provide Verdict
```
✅ APPROVED - Ready to merge
⚠️ CHANGES REQUESTED - List of issues
❌ REJECTED - Major problems
```

---

## Review Criteria

### 1. Specification Compliance (BLOCKING)

**Check:**
- All acceptance criteria met
- API contracts match spec
- Response schemas correct
- Error handling as specified

**Spec Source:** `docs/WAVE2_IMPLEMENTATION_PLAN.md`

**Verdict:**
- ✅ PASS: All criteria met
- ❌ FAIL: Missing criteria → BLOCK

---

### 2. Code Quality (BLOCKING)

**Check:**
```bash
# Style
black src/ tests/ --check
ruff check src/ tests/
mypy src/

# Completeness
grep -r "TODO\|FIXME\|\.\.\." src/  # Should be empty
grep -r "pass$" src/  # Only in __init__.py
```

**Standards:**
- Type hints: REQUIRED
- Docstrings: REQUIRED (Google style)
- No placeholders: REQUIRED
- Follows project patterns: REQUIRED

**Verdict:**
- ✅ PASS: All checks pass
- ⚠️ NEEDS FIXES: Minor style issues
- ❌ FAIL: Major issues → BLOCK

---

### 3. Security (BLOCKING)

**Check:**
```bash
# Security scan
bandit -r src/ -ll

# Manual checks
- No eval/exec/os.system
- No hardcoded secrets
- Input validation present
- Rate limiting where needed
- SQL injection safe
- XSS safe
```

**Verdict:**
- ✅ PASS: No security issues
- 🔴 CRITICAL: Security vulnerability → IMMEDIATE BLOCK

---

### 4. Testing (BLOCKING)

**Check:**
```bash
# Unit tests for new code
pytest tests/unit/test_[feature].py -v

# Coverage
pytest tests/unit/test_[feature].py --cov=src/[module] --cov-report=term

# Regression tests
pytest tests/unit/test_audit_api.py -v  # Wave 1
pytest tests/unit/test_history_api.py -v  # Wave 1
pytest tests/unit/test_portfolio_api.py -v  # Wave 1
pytest tests/integration/test_neo4j_graph.py -v  # Wave 1
```

**Standards:**
- New tests: ALL PASSING (100%)
- Coverage: ≥95% for new code
- Regression: NO FAILURES in Wave 1 tests
- Integration: At least 1 integration test

**Verdict:**
- ✅ PASS: All tests pass, coverage ≥95%, no regressions
- ⚠️ NEEDS FIXES: Some tests fail or coverage low
- ❌ FAIL: Major test failures → BLOCK

---

### 5. Architecture (NON-BLOCKING)

**Check:**
- Follows existing patterns (LangGraph, FastAPI, Pydantic)
- Reuses existing components (no duplication)
- Proper separation of concerns (API/business/data layers)
- API contracts consistent
- Neo4j integration correct (Episode/Fact/Synthesis)
- Error handling consistent

**Verdict:**
- ✅ EXCELLENT: Perfect architecture
- ✅ GOOD: Minor inconsistencies (document for future)
- ⚠️ ACCEPTABLE: Works but could be better (add TODO for refactor)
- ❌ POOR: Major architectural issues → BLOCK

---

### 6. Performance (NON-BLOCKING)

**Check:**
```bash
# Response time test
curl -X POST http://localhost:8000/api/debate/run \
  -H "Content-Type: application/json" \
  -d '{"claim": "test"}' \
  -w "\nTime: %{time_total}s\n"

# Expected: <2s for non-LLM endpoints, <60s for LLM endpoints
```

**Standards:**
- Non-LLM endpoints: <2s
- LLM endpoints: <60s
- No N+1 queries
- Proper caching

**Verdict:**
- ✅ EXCELLENT: Fast and optimized
- ✅ GOOD: Acceptable performance
- ⚠️ SLOW: Document as known issue (not blocking)

---

## Review Checklist Template

```markdown
## Feature [N]: [Name] Review

**Date:** YYYY-MM-DD
**Reviewer:** Claude Sonnet 4.5
**Implementation Agent:** [Agent Name/ID]

### 1. Specification Compliance
- [ ] All acceptance criteria met
- [ ] API contracts match spec
- [ ] Response schemas correct
- [ ] Error handling as specified

**Verdict:** ✅ PASS / ❌ FAIL
**Notes:**

---

### 2. Code Quality
- [ ] black --check passes
- [ ] ruff check passes
- [ ] mypy passes
- [ ] No TODO/FIXME/...
- [ ] Type hints present
- [ ] Docstrings present

**Verdict:** ✅ PASS / ⚠️ NEEDS FIXES / ❌ FAIL
**Notes:**

---

### 3. Security
- [ ] bandit -ll passes
- [ ] No eval/exec/os.system
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] Rate limiting (if needed)

**Verdict:** ✅ PASS / 🔴 CRITICAL
**Notes:**

---

### 4. Testing
- [ ] All new unit tests pass
- [ ] Coverage ≥95%
- [ ] No Wave 1 regressions
- [ ] Integration test included

```
Results:
- Unit tests: [X]/[Y] PASSED
- Coverage: [Z]%
- Regressions: [N] FAILED
```

**Verdict:** ✅ PASS / ⚠️ NEEDS FIXES / ❌ FAIL
**Notes:**

---

### 5. Architecture
- [ ] Follows existing patterns
- [ ] Reuses components
- [ ] Proper separation of concerns
- [ ] API contracts consistent
- [ ] Neo4j integration correct

**Verdict:** ✅ EXCELLENT / ✅ GOOD / ⚠️ ACCEPTABLE / ❌ POOR
**Notes:**

---

### 6. Performance
- [ ] Response time <2s (non-LLM) or <60s (LLM)
- [ ] No N+1 queries
- [ ] Proper caching

**Verdict:** ✅ EXCELLENT / ✅ GOOD / ⚠️ SLOW
**Notes:**

---

## Final Verdict

**Status:** ✅ APPROVED / ⚠️ CHANGES REQUESTED / ❌ REJECTED

**Summary:**

**Blocking Issues:**
1.
2.

**Non-Blocking Suggestions:**
1.
2.

**Next Steps:**
-

---

**Reviewed by:** Claude Sonnet 4.5
**Timestamp:** YYYY-MM-DD HH:MM UTC
```

---

## Communication Protocol

### Implementation Agent → Me

**Format:**
```
Feature [N] implementation complete.

Files changed:
- src/api/routes/debate.py (NEW)
- tests/unit/test_debate_api.py (NEW)

Tests run:
pytest tests/unit/test_debate_api.py -v

Result: 4/4 PASSED

Ready for review.
```

### Me → Implementation Agent

**If APPROVED:**
```
✅ Feature [N] APPROVED

All checks passed. Ready to merge.

Summary:
- Specification: ✅ PASS
- Code Quality: ✅ PASS
- Security: ✅ PASS
- Testing: ✅ PASS (4/4, 98% coverage)
- Architecture: ✅ EXCELLENT
- Performance: ✅ GOOD (<1.5s)

Proceed to next feature.
```

**If CHANGES REQUESTED:**
```
⚠️ Feature [N] CHANGES REQUESTED

Blocking Issues:
1. [Issue description]
2. [Issue description]

Non-Blocking Suggestions:
1. [Suggestion]

Please fix blocking issues and resubmit.
```

**If REJECTED:**
```
❌ Feature [N] REJECTED

Critical Issues:
1. [Critical issue]
2. [Critical issue]

This implementation does not meet requirements.
Please start over or consult spec.
```

---

## Integration Testing

After all 4 features approved individually:

### Final Integration Test
```bash
# Run full test suite
pytest tests/ --ignore=tests/integration/test_websocket_redis.py -v

# Expected results:
# - All new Wave 2 tests pass (25/25)
# - No Wave 1 regressions (47/47 still pass)
# - Overall: [N] passed, [M] failed

# Acceptance:
# - Wave 2: 100% pass
# - Wave 1: 100% pass (no regressions)
```

### Final Approval

**If all 4 features approved + integration test passes:**
```
🎉 WAVE 2 COMPLETE

All 4 features implemented and tested:
✅ Feature 1: Standalone Debate (4h)
✅ Feature 2: Verification Transparency (6h)
✅ Feature 3: Multi-Ticker Compare (8h)
✅ Feature 4: Calibration Pipeline (6h)

Stats:
- New Files: 8
- Modified Files: 10+
- New Code: ~530 LOC
- New Tests: 25/25 PASSING (100%)
- Wave 1 Tests: 47/47 PASSING (no regressions)

Ready for:
1. Final commit
2. Push to remote
3. Deployment
```

---

## Emergency Procedures

### If Implementation Agent is Blocked

**Agent reports:**
```
"Blocked on [issue]. Cannot proceed."
```

**My response:**
```
1. Assess blocker severity
2. If LOW: Provide guidance, agent continues
3. If MEDIUM: Switch to Opus for deep analysis
4. If HIGH: Escalate to user for decision
```

### If Tests Fail Unexpectedly

**Procedure:**
```
1. Verify it's not environment issue (re-run)
2. Check if it's Wave 1 regression (git bisect)
3. If new test: check test correctness vs code correctness
4. Report findings to implementation agent
5. Request fix
```

### If Security Issue Found

**Procedure:**
```
🔴 IMMEDIATE BLOCK

1. Document vulnerability
2. Reject implementation immediately
3. Provide specific fix instructions
4. Re-review after fix
5. Do NOT approve until fixed
```

---

## Metrics Tracking

### Per-Feature Metrics
- Review time (target: <30 min per feature)
- Issues found (goal: <3 blocking per feature)
- Rework cycles (goal: <2 per feature)

### Wave 2 Overall Metrics
- Total review time
- Total issues found
- Features approved first-try vs rework
- Overall quality grade (A+ to F)

---

## Review Schedule

**Estimated Timeline:**

```
Feature 1 (Debate):           Review: 30 min
Feature 2 (Verification):     Review: 45 min
Feature 3 (Multi-Ticker):     Review: 60 min
Feature 4 (Calibration):      Review: 45 min
Final Integration:            Review: 30 min
---------------------------------------------------
Total Review Time:            ~3.5 hours
```

**Availability:** Continuous (ready when implementation agent submits)

---

**Status:** 🟢 READY TO REVIEW

Waiting for implementation agent to complete features.

**Protocol Version:** 1.0
**Last Updated:** 2026-02-11
