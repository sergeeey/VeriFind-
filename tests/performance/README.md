# APE 2026 Load Testing

Week 9 Day 5: Performance validation and stress testing with Locust.

## Overview

Load testing ensures APE 2026 API meets production performance targets:
- **100 concurrent users**
- **P95 response time < 5s**
- **P99 response time < 10s**
- **Throughput > 10 req/sec**
- **Success rate > 95%**

## Installation

```bash
pip install locust
```

## Quick Start

### 1. Start APE API Server

```bash
# Terminal 1: Start API server
cd E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА
uvicorn src.api.main:app --reload
```

### 2. Run Load Test

```bash
# Terminal 2: Run Locust

# Option A: With Web UI (recommended)
locust -f tests/performance/locustfile.py --host http://localhost:8000

# Then open browser: http://localhost:8089
# Enter: 100 users, 10 spawn rate

# Option B: Headless (CI/CD)
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless
```

## User Types

### APEUser (Realistic)
Simulates real user behavior:
- Health checks (rare)
- Submit queries (frequent)
- Poll status (very frequent)
- Retrieve results (medium frequency)
- Wait 1-3 seconds between actions

**Weight: 80%** (default user type)

### HeavyUser (Stress Testing)
Aggressive load for stress testing:
- Rapid-fire query submission
- No waiting for results
- Wait 0.1-0.5 seconds between actions

**Weight: 20%** (stress test scenarios)

## Test Scenarios

### Scenario 1: Light Load (Baseline)
```bash
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 10 \
       --spawn-rate 2 \
       --run-time 2m \
       --headless
```

**Expected Results:**
- P95 < 2s
- P99 < 3s
- 100% success rate

### Scenario 2: Normal Load (Production Simulation)
```bash
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 50 \
       --spawn-rate 5 \
       --run-time 5m \
       --headless
```

**Expected Results:**
- P95 < 4s
- P99 < 7s
- >98% success rate

### Scenario 3: Peak Load (Target)
```bash
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless
```

**Target Results:**
- ✅ P95 < 5s
- ✅ P99 < 10s
- ✅ Throughput > 10 req/sec
- ✅ Success rate > 95%

### Scenario 4: Stress Test (Breaking Point)
```bash
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 200 \
       --spawn-rate 20 \
       --run-time 3m \
       --headless
```

**Goal:** Identify breaking point and failure modes.

## Interpreting Results

### Good Performance
```
Total Requests: 5000
Total Failures: 50 (1%)
Success Rate: 99.00%
Total RPS: 16.67

Response Times:
  Average: 1200ms
  Median: 800ms
  P95: 3500ms ✅
  P99: 6000ms ✅
  Max: 8000ms

Success Criteria:
  P95 < 5s: ✅ PASS (3500ms)
  P99 < 10s: ✅ PASS (6000ms)
  RPS > 10: ✅ PASS (16.67)
  Success > 95%: ✅ PASS (99.00%)
```

### Poor Performance (Needs Optimization)
```
Total Requests: 3000
Total Failures: 300 (10%)
Success Rate: 90.00% ❌
Total RPS: 8.33 ❌

Response Times:
  Average: 6500ms
  Median: 5000ms
  P95: 15000ms ❌
  P99: 25000ms ❌
  Max: 30000ms

Success Criteria:
  P95 < 5s: ❌ FAIL (15000ms)
  P99 < 10s: ❌ FAIL (25000ms)
  RPS > 10: ❌ FAIL (8.33)
  Success > 95%: ❌ FAIL (90.00%)
```

## Exporting Results

### CSV Export
```bash
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless \
       --csv results/load_test
```

Generates:
- `results/load_test_stats.csv` - Request statistics
- `results/load_test_stats_history.csv` - Time-series data
- `results/load_test_failures.csv` - Failure details

### HTML Report
```bash
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless \
       --html results/load_test_report.html
```

## Monitoring During Tests

### Terminal 1: API Server Logs
Watch for errors, warnings, slow queries:
```bash
tail -f logs/ape.log
```

### Terminal 2: System Resources
Monitor CPU, memory, disk I/O:
```bash
# Windows
Task Manager → Performance tab

# Linux
htop
```

### Terminal 3: Database Monitoring
```bash
# PostgreSQL connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Redis connections
redis-cli INFO clients
```

## Common Issues

### Issue 1: Connection Refused
**Symptom:** `ConnectionError: [Errno 111] Connection refused`

**Solution:**
- Ensure API server is running: `curl http://localhost:8000/health`
- Check port 8000 is not blocked by firewall
- Verify `--host` parameter matches server address

### Issue 2: High Failure Rate
**Symptom:** Success rate < 95%

**Causes:**
- Database connection pool exhausted
- Rate limiting triggered
- Timeout errors (queries take >30s)

**Solutions:**
- Increase database connection pool size
- Adjust rate limit thresholds
- Optimize slow queries (add caching)

### Issue 3: P95/P99 Exceeds Targets
**Symptom:** P95 > 5s or P99 > 10s

**Solutions:**
- Add Redis caching for frequent queries
- Optimize database indexes
- Enable query result caching
- Scale horizontally (multiple API instances)

### Issue 4: Low Throughput
**Symptom:** RPS < 10 req/sec

**Causes:**
- Synchronous blocking operations
- Database connection bottleneck
- CPU-bound processing

**Solutions:**
- Use async/await for I/O operations
- Increase worker processes (Gunicorn)
- Optimize CPU-intensive code (vectorization)

## Advanced Usage

### Distributed Load Testing
Run Locust across multiple machines:

**Master:**
```bash
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --master
```

**Workers (on multiple machines):**
```bash
locust -f tests/performance/locustfile.py \
       --worker \
       --master-host 192.168.1.100
```

### Custom Test Duration
```bash
# Run until manually stopped
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000

# Run for specific time
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 10m \
       --headless
```

### Warmup Period
```bash
# Gradually increase load over 2 minutes
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 1 \
       --run-time 10m \
       --headless
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Load Testing

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust

      - name: Start API server
        run: |
          uvicorn src.api.main:app &
          sleep 10

      - name: Run load test
        run: |
          locust -f tests/performance/locustfile.py \
                 --host http://localhost:8000 \
                 --users 50 \
                 --spawn-rate 5 \
                 --run-time 3m \
                 --headless \
                 --csv results/load_test

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: results/
```

## Production Recommendations

1. **Baseline Testing**: Run light load tests weekly
2. **Pre-Release**: Run peak load tests before each release
3. **Monitoring**: Set up alerts for P95/P99 threshold breaches
4. **Capacity Planning**: Test with 2x expected peak load
5. **Gradual Rollout**: Use blue-green deployment for risk mitigation

---

**Last Updated:** Week 9 Day 5
**Version:** 1.0
**Author:** APE 2026 Team
