# APE 2026 Performance Testing Guide

## Overview

This directory contains performance testing scripts for APE 2026 API optimization.

## Quick Start

### 1. Prerequisites

```bash
# Install Python dependencies
pip install aiohttp

# Install k6 (for load testing)
# macOS
brew install k6

# Windows (Chocolatey)
choco install k6

# Linux
curl -s https://dl.k6.io/key.gpg | sudo apt-key add -
sudo apt-get install k6
```

### 2. Start the API

```bash
cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА"
uvicorn src.api.main:app --reload --port 8000
```

### 3. Run Python Performance Tests

```bash
python scripts/performance_test.py
```

**Expected Output:**
```
🚀 APE 2026 Performance Testing
============================================================

📊 Test 1: Single Request (Cold Start)
  ⏱️  Response time: 2.234s
  🔄 Cache status: MISS
  ✅ Status: 200

📊 Test 2: Cache Hit Performance
  Request 1: 2.156s (Cache: MISS)
  Request 2: 0.045s (Cache: HIT)  <-- 98% faster!
  Request 3: 0.042s (Cache: HIT)

📈 Cache Statistics:
   Cache hits: 2
   Cache misses: 1
   Avg cache hit time: 0.044s
   Avg cache miss time: 2.156s
```

### 4. Run k6 Load Test

```bash
# Basic load test
k6 run scripts/load_test.js

# With custom base URL
k6 run -e BASE_URL=http://localhost:8000 scripts/load_test.js

# With specific user count
k6 run --vus 30 --duration 5m scripts/load_test.js
```

**Expected Results:**
```
running (5m00.0s), 00/30 VUs, 1500 complete and 0 interrupted iterations
✓ status is 200
✓ response time < 5s
✓ cache hits > 70%

     data_received..................: 15 MB  50 kB/s
     data_sent......................: 3.2 MB 11 kB/s
     http_req_duration..............: avg=1.23s min=42ms med=1.1s max=4.8s p(90)=2.1s p(95)=3.2s
     cache_hits.....................: 72%    ✓ 72%
```

## Performance Targets

### Before Optimization (Baseline)
| Metric | Value |
|--------|-------|
| p50 latency | 2-3s |
| p95 latency | 5-8s |
| Throughput | 20 req/min |
| Cache hit rate | 0% |

### After Optimization (Target)
| Metric | Value |
|--------|-------|
| p50 latency | <1s |
| p95 latency | <2s |
| Throughput | 60+ req/min |
| Cache hit rate | >70% |

## Optimization Checklist

### Phase 1: Quick Wins (Done ✓)
- [x] Response caching with Redis (5 min TTL)
- [x] Request profiling middleware
- [x] Connection pooling configuration
- [x] Performance metrics endpoint

### Phase 2: Advanced (This Week)
- [ ] Async LLM calls (parallel debate)
- [ ] Lazy loading / Preloading
- [ ] Request batching
- [ ] Database query optimization

### Phase 3: Production (Next Week)
- [ ] Load balancer configuration
- [ ] Auto-scaling rules
- [ ] CDN for static assets
- [ ] Database read replicas

## Monitoring

### Check Cache Statistics
```bash
curl http://localhost:8000/metrics/performance
```

### Monitor Redis
```bash
redis-cli -p 6380 monitor
```

### View Prometheus Metrics
```
http://localhost:8000/metrics
```

## Troubleshooting

### High Memory Usage
```python
# Check memory in Python test
from performance_test import MemoryProfiler
profiler = MemoryProfiler()
print(profiler.get_memory_stats())
```

### Low Cache Hit Rate
1. Check Redis connection: `redis-cli -p 6380 ping`
2. Verify cache keys: `redis-cli -p 6380 keys "ape:cache:*"`
3. Check TTL: `redis-cli -p 6380 ttl <cache_key>`

### Slow LLM Responses
- Check DeepSeek API status
- Verify API key: `echo $DEEPSEEK_API_KEY`
- Try fallback provider (anthropic)

## Interpretation Guide

### Response Time Headers
```
X-Process-Time: 1.234      # Total processing time
X-Cache: HIT               # Cache status (HIT/MISS)
X-Request-Count: 42        # Total requests served
```

### Cache Effectiveness
- **>80% hit rate**: Excellent
- **60-80% hit rate**: Good
- **40-60% hit rate**: Fair (consider increasing TTL)
- **<40% hit rate**: Poor (investigate query patterns)

### Scaling Indicators
If you see:
- `p95 > 5s`: Need optimization or scaling
- `error rate > 5%`: Check error logs
- `memory > 80%`: Scale up or optimize

## Results Interpretation

### Success Criteria
✅ **p50 latency < 1s**  
✅ **p95 latency < 2s**  
✅ **Throughput > 60 req/min**  
✅ **Cache hit rate > 70%**  
✅ **Error rate < 1%**

### Report Generation
```bash
# Run full test suite
python scripts/performance_test.py > results.txt 2>&1

# Run load test with JSON output
k6 run --out json=results.json scripts/load_test.js
```

## Next Steps

After successful performance testing:
1. Update performance baseline in documentation
2. Add performance tests to CI/CD
3. Set up alerts for performance degradation
4. Schedule regular load tests (weekly)

## Support

For issues:
1. Check API logs: `tail -f logs/api.log`
2. Review metrics: `http://localhost:8000/metrics`
3. Run diagnostics: `python scripts/diagnose.py`
