# APE 2026 - System Patterns

## Design Patterns

### 1. Circuit Breaker
**Purpose**: Prevent cascade failures when external APIs fail

**Implementation**:
```python
class CircuitBreaker:
    states: CLOSED → OPEN → HALF_OPEN → CLOSED
    
    CLOSED:  Normal operation
    OPEN:    Failing fast (reject requests)
    HALF_OPEN: Testing recovery
```

**Usage**:
```python
breaker = CircuitBreaker("deepseek", CircuitBreakerConfig(failure_threshold=5))

@breaker
async def call_api():
    return await llm.generate()
```

### 2. Provider Fallback Chain
**Purpose**: LLM redundancy with automatic failover

**Chain**: DeepSeek → Anthropic → OpenAI → Error

```python
class LLMProviderChain:
    async def generate(self, prompt: str) -> str:
        for provider in [deepseek, anthropic, openai]:
            try:
                return await provider.generate(prompt)
            except CircuitBreakerOpen:
                continue  # Try next provider
        raise Exception("All providers failed")
```

### 3. Graceful Degradation
**Purpose**: Continue operating when dependencies fail

**Patterns**:
- DB unavailable → Return empty list (200)
- LLM timeout → Return cached response
- Redis down → In-memory fallback

```python
if not _db_available():
    return PredictionsListResponse(predictions=[], total=0)
```

### 4. Middleware Pipeline
**Purpose**: Cross-cutting concerns (security, monitoring, disclaimers)

**Order**:
1. CORS
2. Request ID
3. Error Logging
4. Prometheus Metrics
5. Rate Limit Headers
6. Security Headers
7. Disclaimer Injection

### 5. Repository Pattern
**Purpose**: Abstract data access

```python
class PredictionStore:
    def get_latest(self, ticker: str) -> Optional[Prediction]
    def get_history(self, ticker: str, limit: int) -> List[Prediction]
    def save(self, prediction: Prediction) -> UUID
```

### 6. Strategy Pattern
**Purpose**: Pluggable data sources

```python
class DataSourceRouter:
    def fetch(self, ticker: str) -> DataFrame:
        if ticker in POPULAR_TICKERS:
            return yfinance_adapter.fetch(ticker)
        else:
            return alpha_vantage_adapter.fetch(ticker)
```

### 7. Agent Pattern
**Purpose**: Multi-agent debate system

```python
class DebateSystem:
    async def debate(self, query: str) -> DebateResult:
        bull = BullAgent()
        bear = BearAgent()
        
        bull_args = await bull.generate_arguments(query)
        bear_args = await bear.generate_arguments(query)
        
        return await self.synthesize(bull_args, bear_args)
```

## Architectural Decisions

### Why Circuit Breaker?
- LLM APIs can be flaky
- Prevents resource exhaustion
- Fast fail improves UX

### Why Redis WebSocket?
- Horizontal scaling (multiple API instances)
- Connection persistence across restarts
- Pub/sub for broadcasting

### Why TimescaleDB?
- Time-series data (stock prices)
- Hypertables for automatic partitioning
- SQL interface for complex queries

### Why Neo4j?
- Graph relationships (facts → sources)
- Temporal queries (facts at time T)
- Episode tracking

## Error Handling Strategy

### Levels
1. **Circuit Breaker**: External API failures
2. **Graceful Degradation**: Return partial data
3. **Exception Handlers**: Format errors (RFC 7807)
4. **Logging**: Structured JSON logs

### Example Flow
```
LLM Timeout
    → Circuit Breaker Opens
    → Fallback to next provider
    → If all fail → Return 503 with retry-after
    → Log error with context
```
