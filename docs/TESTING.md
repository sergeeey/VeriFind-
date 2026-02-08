# Testing Guide — APE Project

## Test Organization

Tests are organized into categories using pytest markers:

| Marker | Description | Run Command |
|--------|-------------|-------------|
| `unit` | Fast unit tests, no external dependencies | `pytest -m unit` |
| `integration` | Integration tests (Docker, databases required) | `pytest -m integration` |
| `realapi` | **Real Claude API tests** (costs money!) | `pytest -m realapi` |
| `slow` | Tests taking >5s | `pytest -m slow` |

## Running Tests

### All Tests (Except Real API)
```bash
# Default: skip expensive API tests
pytest tests/ -m "not realapi"

# Current status: 169/169 passing ✅
```

### Real API Tests (Week 4 Day 2)

**⚠️ IMPORTANT: These tests make REAL Anthropic API calls and cost money!**

**Estimated cost per full run**: $0.15-0.30 (Claude Sonnet 4.5 pricing)

#### Prerequisites
1. Set API key:
   ```bash
   export ANTHROPIC_API_KEY=<your_api_key>
   # Or on Windows:
   set ANTHROPIC_API_KEY=<your_api_key>
   ```

2. Ensure Docker is running (for VEE sandbox)

#### Run Real API Tests
```bash
# Run ONLY real API tests
pytest -m realapi -v

# Expected: 10 tests
# Tests validate:
#   - Claude generates executable code (not hallucinations)
#   - End-to-end: Query → PLAN (real) → VEE → GATE
#   - Data requirements populated correctly
#   - Confidence calibration
#   - Plan validation
```

#### Individual Test Examples
```bash
# Test simple plan generation
pytest tests/integration/test_plan_node_real_api.py::test_real_plan_generation_simple_correlation -v

# Test end-to-end execution
pytest tests/integration/test_plan_node_real_api.py::test_real_plan_end_to_end_execution -v

# Test success criteria
pytest tests/integration/test_plan_node_real_api.py::test_week4_day2_success_criteria -v
```

### Integration Tests (Docker + Databases)
```bash
# Requires: Docker running, TimescaleDB, Neo4j, Redis containers
pytest -m integration -m "not realapi"

# Expected: ~60 integration tests
```

### Unit Tests Only
```bash
# Fast tests, no external dependencies
pytest -m unit

# Expected: ~109 unit tests
```

## Test File Locations

```
tests/
├── unit/                           # Unit tests (fast, mocked)
│   ├── adapters/
│   │   └── test_yfinance_adapter.py
│   ├── orchestration/
│   │   ├── test_doubter_agent.py
│   │   ├── test_fetch_node.py
│   │   ├── test_langgraph_orchestrator.py
│   │   └── test_orchestrator.py
│   ├── truth_boundary/
│   │   └── test_gate.py
│   ├── vee/
│   │   └── test_sandbox_runner.py
│   ├── test_evaluation.py
│   └── test_plan_node.py          # PLAN node (mocked API)
│
├── integration/                    # Integration tests
│   ├── test_chromadb_integration.py
│   ├── test_e2e_pipeline_with_persistence.py
│   ├── test_neo4j_graph.py
│   ├── test_plan_node_real_api.py  # ⭐ NEW: Real API tests
│   ├── test_plan_vee_gate_pipeline.py
│   └── test_timescaledb_storage.py
│
└── conftest.py                     # Shared fixtures
```

## CI/CD Recommendations

### GitHub Actions Example
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest -m unit

  integration-tests:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5.14
      timescaledb:
        image: timescale/timescaledb:latest-pg16
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: pytest -m integration -m "not realapi"

  # Real API tests run on schedule (weekly) to save costs
  real-api-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Only on scheduled runs
    steps:
      - uses: actions/checkout@v4
      - name: Run real API tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: pytest -m realapi -v
```

### Cost Control Strategies

1. **Skip API tests by default**:
   ```bash
   # .gitlab-ci.yml or similar
   default_tests:
     script:
       - pytest -m "not realapi"  # Default: skip expensive tests
   ```

2. **Schedule API tests weekly** (not on every commit):
   ```yaml
   on:
     schedule:
       - cron: '0 0 * * 0'  # Every Sunday at midnight
   ```

3. **Cache API responses** for regression testing:
   ```python
   # tests/fixtures/cached_plans.json
   # Store successful plan generation outputs
   ```

## Success Criteria Status

### Week 4 Day 2: Real PLAN Node Integration
- [ ] PLAN Node generates executable code via real API
- [ ] No hallucinations (all generated code runs in VEE)
- [ ] Data requirements populated correctly
- [ ] Confidence calibration functional
- [ ] API stats tracking works
- [ ] Dependency graph validation (no cycles)
- [ ] End-to-end: Query → PLAN (real) → VEE → GATE

**Status**: Tests created, awaiting API key validation

### Overall Test Coverage

| Component | Unit Tests | Integration Tests | Real API Tests | Status |
|-----------|------------|-------------------|----------------|--------|
| VEE Sandbox | 16 | 9 | - | ✅ |
| YFinance Adapter | 14 | - | - | ✅ |
| Truth Boundary Gate | 14 | 6 | - | ✅ |
| PLAN Node | 17 | - | **10** | ⏳ API tests |
| Orchestrator | 11 | - | - | ✅ |
| LangGraph | 15 | - | - | ✅ |
| TimescaleDB | - | 11 | - | ✅ |
| Neo4j | - | 10 | - | ✅ |
| FETCH Node | 11 | - | - | ✅ |
| Doubter Agent | 7 | - | - | ✅ |
| ChromaDB | - | 10 | - | ✅ |
| E2E Pipeline | - | 6 | - | ✅ |
| **Total** | **109** | **60** | **10** | **179 tests** |

## Debugging Failed Tests

### Common Issues

1. **Docker not running**:
   ```
   ERROR: Cannot connect to Docker daemon
   FIX: Start Docker Desktop
   ```

2. **Database containers not started**:
   ```bash
   docker compose up -d  # Start all services
   ```

3. **API key missing (real API tests)**:
   ```
   SKIPPED: ANTHROPIC_API_KEY not set
   FIX: export ANTHROPIC_API_KEY=<key>
   ```

4. **Port conflicts**:
   ```
   ERROR: Port 5433 already in use
   FIX: docker compose down && docker compose up -d
   ```

### Test Logs
```bash
# View detailed logs
pytest tests/ -v --tb=long --log-cli-level=DEBUG

# Save logs to file
pytest tests/ -v > test_output.log 2>&1
```

## Performance Benchmarks

| Test Suite | Duration | Requirements |
|------------|----------|--------------|
| Unit tests | ~10s | None |
| Integration tests (no API) | ~80s | Docker, databases |
| Real API tests | ~30-60s | API key, $0.30 cost |
| **Full suite** | ~2-3 minutes | All requirements |

---

*Last Updated: 2026-02-08 (Week 4 Day 2)*
*Contact: See CLAUDE.md for testing guidelines*
