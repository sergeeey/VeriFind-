# APE 2026 - Technical Specification

## System Architecture

### Data Flow
```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Query  │───▶│  Router  │───▶│   Plan   │───▶│  Fetch   │
└─────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                         ┌──────────────────────────┘
                         ▼
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Response│◀───│ Synthesis│◀───│  Debate  │◀───│   VEE    │
└─────────┘    └──────────┘    └──────────┘    └──────────┘
                      ▲              ▲              ▲
                      │              │              │
                 ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
                 │  Bull   │    │  Bear   │    │ Sandbox │
                 │  Agent  │    │  Agent  │    │  Runner │
                 └─────────┘    └─────────┘    └─────────┘
```

## Core Components

### 1. API Layer (FastAPI)
```python
src/api/
├── main.py              # FastAPI app
├── config.py            # Pydantic settings (NOW WITH PERFORMANCE SETTINGS)
├── error_handlers.py    # Exception handling
├── cache_simple.py      # Route-level caching (NEW)
├── middleware/          
│   ├── cache.py         # Response cache middleware (NEW)
│   ├── profiling.py     # Performance profiling (NEW)
│   ├── security.py      # Security headers
│   ├── rate_limit.py    # Rate limiting
│   └── disclaimer.py    # Legal disclaimer
├── routes/              
│   ├── health.py        # /health, /ready, /live, /metrics/performance
│   ├── analysis.py      # /api/analyze (WITH CACHE)
│   ├── predictions.py   # /api/predictions/*
│   └── data.py          # /api/data/*
└── monitoring.py        # Prometheus metrics
```

### 2. Cache Layer (Week 10 Addition)

#### Route-Level Cache (Recommended)
```python
# src/api/cache_simple.py
CachedAnalyze:
  - get(request, body) → Optional[dict]
  - set(request, body, result, ttl=300)
  
# Usage in analysis.py
@router.post("/analyze")
async def analyze_query(...):
    # Check cache
    cached = await analyze_cache.get(raw_request, request)
    if cached:
        return AnalysisResponse(**cached)  # <0.1s response!
    
    # Process...
    result = await orchestrator.process_query_async(...)
    
    # Cache result
    await analyze_cache.set(raw_request, request, result.dict())
    return result
```

#### Middleware Cache (Alternative)
```python
# src/api/middleware/cache.py
ResponseCacheMiddleware:
  - Redis-based
  - 5 minute TTL
  - SHA256 cache keys
  - Automatic invalidation
```

**Performance Comparison:**
| Method | Cache HIT | Implementation |
|--------|-----------|----------------|
| Route-Level | <0.1s | Simple, reliable |
| Middleware | ~2s (with issues) | Complex, has bugs |

**Recommendation**: Use route-level cache.

### 3. Profiling Layer (Week 10 Addition)
```python
# src/api/middleware/profiling.py
ProfilingMiddleware:
  - Tracks request duration
  - Logs slow requests (>2s)
  - Adds X-Process-Time header
  - Stores metrics for analysis

# Metrics endpoint
GET /metrics/performance → {
    "cache": {
        "hit_rate": 36.36,
        "keys_count": 0
    },
    "profiling": {
        "slow_requests": 5,
        "avg_time": 45.2
    }
}
```

### 4. Resilience Layer
```python
src/resilience/
└── circuit_breaker.py
    ├── CircuitBreaker           # State machine
    ├── CircuitState             # CLOSED/OPEN/HALF_OPEN
    └── LLMProviderChain         # Fallback chain
        DeepSeek → Anthropic → OpenAI → Error
```

**Usage**:
```python
breaker = CircuitBreaker("deepseek", CircuitBreakerConfig())

@breaker
async def call_llm(prompt: str) -> str:
    return await deepseek_client.generate(prompt)
```

### 5. Database Layer

**Neo4j (Graph)**:
- Nodes: Facts, Episodes, Queries
- Relationships: VERIFIED_BY, PART_OF, DEBATE
- Port: 7688

**TimescaleDB (Time-series)**:
- Table: `predictions` (hypertable)
- Columns: ticker, target_date, price_low/base/high, actual_price, accuracy_band
- Port: 5433

**Redis (Cache)**:
- Port: 6380
- Usage: Response caching, session storage
- ⚠️ **STATUS**: Container not running (needs restart)

### 6. Performance Configuration

```python
# src/api/config.py
class APISettings:
    # Connection Pooling
    db_pool_size: int = 20
    db_max_overflow: int = 10
    redis_max_connections: int = 50
    
    # Cache Settings
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_enabled: bool = True
    
    # Profiling
    profiling_enabled: bool = True
    profiling_slow_threshold: float = 2.0
    
    # LLM Timeout
    llm_timeout_seconds: int = 30
    llm_retry_attempts: int = 3
```

## API Endpoints

### Health & Monitoring
```
GET  /health              → {"status": "healthy", "components": {...}}
GET  /ready               → {"status": "ready", "ready": true}
GET  /live                → {"status": "alive"}
GET  /metrics             → Prometheus metrics
GET  /metrics/performance → Cache & profiling stats (NEW)
GET  /disclaimer          → Legal disclaimer text
```

### Analysis
```
POST /api/analyze        → Sync analysis with caching (NEW)
POST /api/query          → Async query (returns query_id)
GET  /api/status/{id}    → Query execution status
POST /api/debate         → Multi-perspective analysis
```

### Predictions
```
GET  /api/predictions/              → List all predictions
GET  /api/predictions/{ticker}/latest
GET  /api/predictions/{ticker}/history
GET  /api/predictions/{ticker}/corridor
GET  /api/predictions/track-record  → Accuracy metrics
POST /api/predictions/check-actuals → Update with real prices
```

### Data
```
GET  /api/data/tickers              → Available tickers
POST /api/data/fetch                → Trigger data fetch
GET  /api/facts                     → Verified facts
GET  /api/episodes                  → Analysis episodes
```

## Performance Targets

| Endpoint | Target | Current | Status |
|----------|--------|---------|--------|
| /health | < 10ms | ~10ms | ✅ |
| /api/analyze (cached) | < 0.1s | 2.0s | ⚠️ |
| /api/analyze (first) | < 5s | 60-75s | ✅ (AI time) |
| /api/predictions/ | < 100ms | ~100ms | ✅ |
| Cache Hit Rate | > 70% | 36% | ⚠️ |
| Throughput | 60/min | ~20/min | ⚠️ |

## Security

### Headers (all responses)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self' ...
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-Cache: HIT/MISS (NEW)
X-Process-Time: 1.234 (NEW)
```

### API Key Management
- Current: `.env` file (local only)
- Risk: P1 tech debt (acceptable for MVP)
- Future: HashiCorp Vault/AWS Secrets Manager

## Configuration

### Environment Variables
```bash
# Required
SECRET_KEY=<32+ chars>
DEEPSEEK_API_KEY=sk-...          # NEW
ANTHROPIC_API_KEY=sk-ant-...     # Fallback
OPENAI_API_KEY=sk-proj-...       # Fallback
NEO4J_PASSWORD=<strong>
POSTGRES_PASSWORD=<strong>

# Optional
REDIS_HOST=localhost
REDIS_PORT=6380
CACHE_ENABLED=true
PROFILING_ENABLED=true
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## Testing

### Performance Tests
```bash
# Python test
python scripts/performance_test.py

# k6 load test
k6 run scripts/load_test.js

# Quick validation
python scripts/quick_test.py
```

### Test Scenarios
1. **Cache HIT Test**: Same query twice → Second should be <0.1s
2. **Validation Test**: Short query (<10 chars) → Should return 422
3. **Gold Forecast**: Real commodity query → Should return 200 with data
4. **Bitcoin Forecast**: Crypto query → Should return risk metrics

## Resilience Patterns

### Circuit Breaker
- **Failure Threshold**: 5 errors
- **Timeout**: 60 seconds
- **States**: CLOSED → OPEN → HALF_OPEN → CLOSED

### Fallback Chain
```
DeepSeek (primary) → Anthropic (fallback) → OpenAI (fallback) → Error
```

### Graceful Degradation
- DB unavailable → Empty response (200)
- LLM unavailable → Circuit breaker open
- Redis unavailable → In-memory cache (slow)

## Deployment Notes

### Docker Services
```yaml
# Required
redis:
  image: redis:latest
  ports:
    - "6380:6379"
  
neo4j:
  image: neo4j:5.x
  ports:
    - "7688:7687"
    - "7475:7474"

timescaledb:
  image: timescale/timescaledb:latest-pg15
  ports:
    - "5433:5432"
```

### Startup Order
1. Start databases (Neo4j, TimescaleDB, Redis)
2. Wait for health checks
3. Start API: `uvicorn src.api.main:app --reload --port 8000`
4. Verify: `curl http://localhost:8000/health`

## Known Issues

1. **Redis not responding** (Port 6380)
   - Workaround: API works without cache (slower)
   - Fix: `docker run -d --name redis-ape -p 6380:6379 redis:latest`

2. **Cache middleware slow**
   - Workaround: Use route-level cache
   - Fix: Disable middleware cache in main.py

3. **Demo mode responses**
   - Workaround: None (requires API key)
   - Fix: Set DEEPSEEK_API_KEY in .env
