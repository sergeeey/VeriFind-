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
├── config.py            # Pydantic settings
├── error_handlers.py    # Exception handling
├── middleware/          # Security, rate limit, disclaimer
├── routes/              # Endpoints
│   ├── health.py        # /health, /ready, /live
│   ├── analysis.py      # /api/analyze, /api/query
│   ├── predictions.py   # /api/predictions/*
│   └── data.py          # /api/data/*
└── monitoring.py        # Prometheus metrics
```

### 2. Resilience Layer
```python
src/resilience/
└── circuit_breaker.py
    ├── CircuitBreaker           # State machine
    ├── CircuitState             # CLOSED/OPEN/HALF_OPEN
    └── LLMProviderChain         # Fallback chain
```

**Usage**:
```python
breaker = CircuitBreaker("deepseek", CircuitBreakerConfig())

@breaker
async def call_llm(prompt: str) -> str:
    return await deepseek_client.generate(prompt)
```

### 3. Database Layer

**Neo4j (Graph)**:
- Nodes: Facts, Episodes, Queries
- Relationships: VERIFIED_BY, PART_OF, DEBATE

**TimescaleDB (Time-series)**:
- Table: `predictions` (hypertable)
- Columns: ticker, target_date, price_low/base/high, actual_price, accuracy_band

### 4. WebSocket Layer
```python
src/api/websocket_redis.py
├── RedisConnectionManager     # Pub/sub broadcasting
├── connect()                  # Register client
└── broadcast()                # Publish message
```

## API Endpoints

### Health & Monitoring
```
GET  /health          → {"status": "healthy", "components": {...}}
GET  /ready           → {"status": "ready", "ready": true}
GET  /live            → {"status": "alive"}
GET  /metrics         → Prometheus metrics
```

### Analysis
```
POST /api/analyze     → Sync analysis with disclaimer
POST /api/query       → Async query (returns query_id)
GET  /api/status/{id} → Query execution status
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
```

## Security

### Headers (all responses)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self' ...
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
```

### API Key Management
- Current: `.env` file (local only)
- Future: HashiCorp Vault/AWS Secrets Manager
- Risk: P1 tech debt (acceptable for MVP)

## Configuration

### Environment Variables
```bash
# Required
SECRET_KEY=<32+ chars>
ANTHROPIC_API_KEY=sk-...
NEO4J_PASSWORD=<strong>
POSTGRES_PASSWORD=<strong>

# Optional
REDIS_HOST=localhost
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## Monitoring

### Prometheus Metrics
```python
# HTTP
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint}

# Business
ape_queries_total{status}
ape_accuracy{window}
websocket_connections_total

# External
external_api_requests_total{service, status}
```

### Health Checks
- **Liveness**: `/live` → k8s livenessProbe
- **Readiness**: `/ready` → k8s readinessProbe
- **Health**: `/health` → General health with component status

## Performance Targets

| Endpoint | Avg Latency | P95 | RPS |
|----------|-------------|-----|-----|
| /health | < 10ms | < 50ms | 1000+ |
| /api/predictions/ | < 100ms | < 500ms | 100+ |
| /api/query | < 5s | < 10s | 10+ |

## Resilience Patterns

### Circuit Breaker
- **Failure Threshold**: 5 errors
- **Timeout**: 60 seconds
- **States**: CLOSED → OPEN → HALF_OPEN → CLOSED

### Fallback Chain
```
DeepSeek → Anthropic → OpenAI → Error
```

### Graceful Degradation
- DB unavailable → Empty response (200)
- LLM unavailable → Circuit breaker open
- Redis unavailable → In-memory WebSocket
