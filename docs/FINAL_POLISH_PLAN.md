# Final Polish Plan — Production Perfection

**Goal:** Довести APE 2026 до эталонного состояния
**Current:** 7.5/10 → **Target:** 9.5/10
**Time Estimate:** 3-4 hours

---

## 🎯 Критерии эталона

### Technical Excellence
- ✅ All tests passing (no SQLAlchemy errors)
- ✅ 100% test coverage на критических компонентах
- ✅ No warnings in pytest
- ✅ Clean linting (black, ruff, mypy)
- ✅ Documentation complete

### Production Ready
- ✅ Docker deployment готов
- ✅ Environment validation
- ✅ Health checks comprehensive
- ✅ Monitoring dashboards
- ✅ Error tracking configured

### Code Quality
- ✅ No TODOs or placeholders
- ✅ All docstrings complete
- ✅ Type hints on all functions
- ✅ Consistent code style

---

## 📋 Action Plan

### PHASE 1: Fix SQLAlchemy Compatibility (30 min)

**Problem:** SQLAlchemy 2.0.36 incompatible with Python 3.13.5

**Option A: Downgrade SQLAlchemy** (quick fix)
```bash
# In requirements.txt
sqlalchemy==2.0.25  # Last stable with Python 3.13

# Test
pip install -r requirements.txt
pytest tests/integration/test_api_critical.py -v
```

**Option B: Pin Python 3.11** (recommended)
```bash
# Update conda environment
conda create -n ape311 python=3.11
conda activate ape311
pip install -r requirements.txt

# Verify
python --version  # Should be 3.11.x
pytest tests/integration/ -v
```

**Deliverable:** All API tests passing

---

### PHASE 2: Clean Up Warnings (20 min)

**Current:** 45-77 warnings in pytest output

**Actions:**
1. Fix deprecation warnings
   ```python
   # Replace @app.on_event with lifespan context
   # src/api/app_factory.py
   ```

2. Suppress known warnings
   ```python
   # pytest.ini
   filterwarnings =
       ignore::DeprecationWarning:neo4j
       ignore::PytestUnraisableExceptionWarning
   ```

3. Fix missing __init__.py warnings

**Deliverable:** <10 warnings total

---

### PHASE 3: Test Coverage to 95%+ (45 min)

**Current Coverage Gaps:**
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html to see gaps
```

**Priority Areas:**
1. `src/api/app_factory.py` (new file, likely 0% coverage)
   - Add tests for create_app()
   - Test middleware configuration order
   - Test router registration

2. `src/debate/multi_llm_agents.py` (Bear agent JSON unwrap)
   - Test JSON in markdown blocks
   - Test plain JSON (backward compat)
   - Test error handling

3. `src/debate/parallel_orchestrator.py` (compliance fields)
   - Test _calculate_model_agreement()
   - Test disclaimer propagation

**Deliverable:** 95%+ coverage on critical modules

---

### PHASE 4: Type Checking (15 min)

**Run mypy on critical modules:**
```bash
mypy src/api/main.py
mypy src/api/app_factory.py
mypy src/debate/parallel_orchestrator.py
mypy src/debate/multi_llm_agents.py
```

**Fix type issues:**
- Add return type hints
- Fix Optional vs None
- Add missing imports for TYPE_CHECKING

**Deliverable:** mypy passes on all critical files

---

### PHASE 5: Documentation Polish (30 min)

**Update files:**

1. **README.md** (root)
   - Update installation instructions
   - Add quick start guide
   - Update architecture diagram

2. **CLAUDE.md** (update current status)
   ```markdown
   **Phase:** Week 13 Day 2 COMPLETE
   **Status:** Production Ready (9.5/10)
   **Tests:** 11/11 regression + 47+ total
   **Coverage:** 95%+
   ```

3. **API Documentation**
   - Add OpenAPI examples
   - Document compliance fields
   - Add error response examples

**Deliverable:** Complete, accurate documentation

---

### PHASE 6: Docker & Deployment (60 min)

**1. Docker Compose Validation**
```bash
docker-compose config  # Validate syntax
docker-compose up -d  # Start services
docker-compose ps     # Verify all running

# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

**2. Environment Validation Script**
Create `scripts/validate_env.py`:
```python
"""Validate environment before deployment."""
import os
import sys

required_vars = [
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "FRED_API_KEY",
    # ... all required vars
]

missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"❌ Missing: {missing}")
    sys.exit(1)

print("✅ Environment validated")
```

**3. Production Checklist**
- [ ] All secrets in .env (not hardcoded)
- [ ] CORS origins configured correctly
- [ ] Rate limits set appropriately
- [ ] Logging level = INFO (not DEBUG)
- [ ] Monitoring enabled
- [ ] Database migrations applied

**Deliverable:** Docker deployment tested and working

---

### PHASE 7: Performance Optimization (45 min)

**1. Response Caching**
- Enable route-level caching for /api/status
- Cache Golden Set results (30 min TTL)

**2. Database Connection Pooling**
```python
# Check current pool settings
# src/storage/timescale_client.py
pool_size = 20  # Increase from default 5
max_overflow = 10
```

**3. Async Optimization**
- Ensure all I/O operations are async
- Add timeout to external API calls

**4. Benchmark**
```bash
# Baseline performance
ab -n 100 -c 10 http://localhost:8000/health

# Golden Set performance
python eval/run_golden_set.py --limit 5
# Target: <20s avg per query
```

**Deliverable:** <20s avg query time, 100 req/s health endpoint

---

### PHASE 8: Security Hardening (30 min)

**1. Dependency Audit**
```bash
pip-audit  # Check for known vulnerabilities
# Fix any HIGH/CRITICAL issues
```

**2. Secrets Scanning**
```bash
# Ensure no secrets in git history
git log -p | grep -i "api_key\|password\|secret"

# Add pre-commit hook
# .git/hooks/pre-commit
gitleaks detect --no-git
```

**3. CORS Configuration**
```python
# Restrictive CORS in production
CORS_ORIGINS = ["https://ape2026.com"]  # Not "*"
```

**4. Rate Limiting**
```python
# Verify rate limits are enforced
# test: curl -X POST http://localhost:8000/api/analyze (100 times)
```

**Deliverable:** Security audit passing

---

### PHASE 9: Monitoring & Observability (30 min)

**1. Prometheus Metrics**
```python
# Add custom metrics
from prometheus_client import Counter, Histogram

hallucination_rate = Gauge("hallucination_rate", "Current hallucination rate")
query_duration = Histogram("query_duration_seconds", "Query processing time")
```

**2. Structured Logging**
```python
# Ensure all logs are JSON in production
# src/api/error_handlers.py - already done ✅
```

**3. Health Check Enhancement**
```python
# src/api/routes/health.py
# Add dependency checks:
# - Database connectivity
# - External API availability
# - Memory/CPU usage
```

**4. Alerting**
```python
# Set up alerts for:
# - Hallucination rate > 5%
# - Error rate > 10%
# - Response time > 30s
# - Memory usage > 80%
```

**Deliverable:** Comprehensive monitoring dashboard

---

### PHASE 10: Final Validation (30 min)

**Complete Test Suite:**
```bash
# All tests
pytest -v --cov=src --cov-report=term-missing

# Should show:
# - 50+ tests passing
# - 95%+ coverage
# - <10 warnings
# - 0 errors
```

**Golden Set Validation:**
```bash
# Full 30 queries
python eval/run_golden_set.py eval/golden_set.json

# Expected:
# - 30/30 success
# - 0% hallucination rate
# - <25s avg time
# - <$0.10 total cost
```

**Integration Test:**
```bash
# Start full stack
docker-compose up -d

# Run real query
curl -X POST http://localhost:8000/api/analyze-debate \
  -H "Content-Type: application/json" \
  -d '{"query":"Analyze AAPL stock","tickers":["AAPL"]}'

# Verify:
# - 3 perspectives (bull, bear, arbiter)
# - All compliance fields present
# - Disclaimer included
# - Response time <30s
```

**Deliverable:** All validation passing

---

## 🎯 Success Criteria

### Technical
- ✅ 0 test failures
- ✅ 95%+ test coverage
- ✅ <10 pytest warnings
- ✅ mypy passing on critical files
- ✅ All linters passing (black, ruff)

### Functional
- ✅ Golden Set: 30/30 success, 0% hallucination
- ✅ All compliance fields present
- ✅ All 3 agent perspectives working
- ✅ Regression tests protecting critical fixes

### Performance
- ✅ <20s avg query time
- ✅ 100 req/s health endpoint
- ✅ <$0.10 per 30 queries

### Security
- ✅ No known vulnerabilities (pip-audit)
- ✅ No secrets in code
- ✅ CORS configured correctly
- ✅ Rate limiting enforced

### Deployment
- ✅ Docker compose working
- ✅ All health checks passing
- ✅ Monitoring enabled
- ✅ Documentation complete

---

## 📊 Progress Tracking

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Fix SQLAlchemy | 30m | ⏳ |
| 2 | Clean warnings | 20m | ⏳ |
| 3 | Test coverage | 45m | ⏳ |
| 4 | Type checking | 15m | ⏳ |
| 5 | Documentation | 30m | ⏳ |
| 6 | Docker setup | 60m | ⏳ |
| 7 | Performance | 45m | ⏳ |
| 8 | Security | 30m | ⏳ |
| 9 | Monitoring | 30m | ⏳ |
| 10 | Final validation | 30m | ⏳ |

**Total:** ~5.5 hours → **Target:** 9.5/10

---

## 🚀 Execution Order

**Recommended sequence:**

1. **Phase 1** (CRITICAL) - Fix SQLAlchemy → all tests passing
2. **Phase 3** - Test coverage → confidence in code
3. **Phase 2** - Clean warnings → clean output
4. **Phase 4** - Type checking → catch bugs early
5. **Phase 6** - Docker → deployment ready
6. **Phase 7** - Performance → user experience
7. **Phase 8** - Security → production safe
8. **Phase 9** - Monitoring → observability
9. **Phase 5** - Documentation → share knowledge
10. **Phase 10** - Final validation → ship it!

---

**Start with Phase 1?** Исправим SQLAlchemy чтобы получить clean test run?
