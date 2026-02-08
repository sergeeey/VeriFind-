# System Patterns — APE 2026

Архитектурные паттерны, соглашения и best practices для проекта.

---

## Core Architectural Patterns

### 1. **Truth Boundary Pattern** (Уникальный для APE)

**Проблема:** LLM галлюцинируют числа
**Решение:** Архитектурное разделение ответственности

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  LLM Layer  │ ──▶  │  Code Layer  │ ──▶  │  VEE Layer  │
│             │      │              │      │             │
│ Generates:  │      │ Generates:   │      │ Executes:   │
│ - Plan      │      │ - SQL        │      │ - Query     │
│ - Code      │      │ - Python     │      │ - Script    │
│ - Explanation│      │ - API calls  │      │ - Returns   │
│             │      │              │      │  VerifiedFact│
│ ❌ NO numbers│      │ ❌ NO numbers│      │ ✅ Numbers  │
└─────────────┘      └──────────────┘      └─────────────┘
```

**Enforcement:**
- Truth Boundary Gate проверяет каждое число в тексте
- Если число не имеет `FactRef` → BLOCK
- Если `FactRef` не существует в `EvidenceBundle` → BLOCK

**Code Example:**
```python
# ❌ BAD (LLM generating numbers directly)
def bad_volatility_report(symbol: str) -> str:
    return f"The volatility of {symbol} is 15.3%"  # Hallucination risk!

# ✅ GOOD (Code-as-Truth)
def good_volatility_report(symbol: str) -> Report:
    # 1. Code generates fact
    fact = execute_in_vee(f"""
        import yfinance as yf
        data = yf.download('{symbol}', period='30d')
        volatility = data['Close'].pct_change().std()
        return {{'value': volatility, 'unit': 'ratio'}}
    """)

    # 2. LLM references fact, doesn't generate number
    return f"The volatility of {symbol} is {{{{FactRef({fact.id})|{fact.value:.1%}}}}}"
```

---

### 2. **Fail-Closed Pattern**

**Принцип:** При неопределенности → UNCERTAIN, не выдумывать

```python
def fail_closed_example(query: str, confidence: float, evidence_coverage: float) -> Response:
    if confidence < 0.70:
        return Response(
            verdict="UNCERTAIN",
            reason="Confidence below threshold (70%)",
            action="HITL_ESCALATE"
        )

    if evidence_coverage < 0.90:
        return Response(
            verdict="UNCERTAIN",
            reason="Evidence coverage insufficient (<90%)",
            action="REQUEST_MORE_DATA"
        )

    # Only return confident answer if all checks pass
    return Response(verdict="CONFIDENT", data=final_report)
```

**Triggers:**
- Confidence < 70%
- Evidence Coverage < 90%
- Sign flip в sensitivity analysis
- Doubter verdict = NEED_HUMAN
- Temporal violation detected
- Truth Gate BLOCK

---

### 3. **Verifiable Execution Environment (VEE) Pattern**

**Isolation Layers:**
```yaml
Network:
  allowed_hosts:
    - api.stlouisfed.org  # FRED
    - query.yahooapis.com # Yahoo Finance
  blocked: everything else

Filesystem:
  read: /workspace (sandbox only)
  write: /workspace/output (sandbox only)
  blocked: /host/*

Resources:
  memory: 2GB hard limit
  timeout: 60 sec per execution
  cpu: 2 cores
```

**Security Checks (Pre-Execution):**
```python
def validate_code_safety(code: str) -> ValidationResult:
    forbidden_patterns = [
        r"import os",           # OS interaction
        r"import subprocess",   # Shell access
        r"open\(['\"]\/",       # Absolute path access
        r"__import__",          # Dynamic imports
        r"eval\(",              # Code injection
        r"exec\(",              # Code injection
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, code):
            return ValidationResult(safe=False, reason=f"Forbidden pattern: {pattern}")

    return ValidationResult(safe=True)
```

---

### 4. **Temporal Integrity Pattern** (Финансовая специфика)

**Проблема:** Look-ahead bias — использование будущих данных в прошлом

```python
@dataclass
class VerifiedFact:
    asof_timestamp: datetime      # Когда факт истинен
    publication_lag: timedelta    # Задержка публикации

    @property
    def available_at(self) -> datetime:
        """Когда факт стал известен рынку"""
        return self.asof_timestamp + self.publication_lag

def check_temporal_integrity(fact: VerifiedFact, episode: EpisodeState) -> bool:
    if fact.available_at > episode.asof_timestamp:
        raise TemporalViolation(
            f"Fact available at {fact.available_at}, but query asof {episode.asof_timestamp}"
        )
    return True
```

**Publication Lags (Defaults):**
```python
PUBLICATION_LAGS = {
    "yfinance": timedelta(seconds=0),     # Real-time
    "fred_gdp": timedelta(days=90),       # Quarterly + revision
    "fred_cpi": timedelta(days=14),       # Monthly + 2 weeks
    "sec_10k": timedelta(days=45),        # 10-K filing deadline
    "earnings": timedelta(days=1),        # Next-day after call
}
```

---

### 5. **Multi-Agent Debate Pattern**

**Roles (Обязательные):**
```python
DEBATE_AGENTS = {
    "Bull": {
        "bias": "optimistic",
        "focus": "opportunities, positive trends",
        "model": "deepseek-v3"
    },
    "Bear": {
        "bias": "pessimistic",
        "focus": "risks, threats, data quality issues",
        "model": "deepseek-v3"
    },
    "Quant": {
        "bias": "neutral",
        "focus": "statistical significance, assumptions",
        "model": "deepseek-v3"
    }
}
```

**Consensus Calculation:**
```python
def calculate_consensus(reports: List[PanelReport]) -> ConsensusMetrics:
    confidences = [r.confidence for r in reports]

    # Vote entropy (0 = perfect agreement, 1 = max disagreement)
    vote_entropy = -sum(p * log(p) for p in confidences if p > 0) / log(len(confidences))

    # Pairwise contradiction rate
    contradictions = 0
    for i, r1 in enumerate(reports):
        for r2 in reports[i+1:]:
            if contradicts(r1.conclusion, r2.conclusion):
                contradictions += 1
    contradiction_rate = contradictions / (len(reports) * (len(reports) - 1) / 2)

    return ConsensusMetrics(
        vote_entropy=vote_entropy,
        contradiction_rate=contradiction_rate,
        confidence_penalty=vote_entropy * 0.5 + contradiction_rate * 0.5
    )
```

---

### 6. **Sensitivity Harness Pattern**

**Проблема:** Выводы чувствительны к параметрам (окно, метод, outliers)

```python
def run_sensitivity_analysis(
    base_step: PlanStep,
    base_fact: VerifiedFact,
    parameters_to_vary: Dict[str, List[Any]]
) -> SensitivityReport:
    """
    Example:
    parameters_to_vary = {
        "window": ["20d", "30d", "60d", "90d"],
        "method": ["std", "ewm"],
    }
    """
    base_value = base_fact.value
    variations = []

    for param_name, param_values in parameters_to_vary.items():
        for param_value in param_values:
            variant_step = base_step.copy()
            variant_step.parameters[param_name] = param_value

            variant_fact = execute_step(variant_step)
            delta = (variant_fact.value - base_value) / base_value

            variations.append({
                "param": param_name,
                "value": param_value,
                "result": variant_fact.value,
                "delta_pct": delta
            })

    # Check for sign flips (критично!)
    sign_flips = any(
        (base_value > 0 and v["result"] < 0) or
        (base_value < 0 and v["result"] > 0)
        for v in variations
    )

    if sign_flips:
        # Резко снижаем confidence
        return SensitivityReport(
            stability="UNSTABLE",
            sign_flip=True,
            confidence_penalty=0.7,  # 70% penalty
            action="BLOCK_OR_WARN"
        )

    # Sensitivity score (устойчивость)
    deltas = [v["delta_pct"] for v in variations]
    sensitivity_score = 1.0 / (1.0 + np.std(deltas))

    return SensitivityReport(
        stability="STABLE" if sensitivity_score > 0.8 else "MODERATE",
        sign_flip=False,
        sensitivity_score=sensitivity_score,
        confidence_penalty=max(0, 1.0 - sensitivity_score)
    )
```

---

### 7. **Evidence Provenance Pattern**

**Каждый факт хранит полную провенанс:**
```python
@dataclass
class VerifiedFact:
    # Value
    value: Any
    unit: str  # "USD", "percent", "ratio", "count"

    # Provenance (откуда пришло)
    source: {
        "name": str,          # "yfinance", "FRED", "clickhouse"
        "version": str,       # API/library version
        "query_hash": str,    # SHA256(query)
        "output_hash": str,   # SHA256(result)
    }
    method: str  # "sql_query", "python_script", "api_call"

    # Temporal
    asof_timestamp: datetime
    publication_lag: timedelta
    window_definition: Optional[str]  # "rolling_30d", "monthly", "ytd"

    # Audit
    created_at: datetime
    execution_log_ref: UUID  # Ссылка на полный лог
```

**Lineage Graph (Neo4j):**
```cypher
// Episode зависит от фактов
(episode:Episode)-[:USED_FACT]->(fact:VerifiedFact)

// Derived факты зависят от verified фактов
(derived:DerivedFact)-[:DERIVED_FROM]->(fact:VerifiedFact)

// Факты создаются через execution logs
(fact:VerifiedFact)-[:CREATED_BY]->(log:ExecutionLog)

// Query для трассировки: "откуда взялось это число?"
MATCH path = (e:Episode {id: $episode_id})-[:USED_FACT*]->(f:VerifiedFact)
RETURN path
```

---

## Code Style Conventions

### Python Style
```python
# Pydantic models для всех schemas
from pydantic import BaseModel, Field

class VerifiedFact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    value: float
    unit: str

    class Config:
        frozen = True  # Immutable

# Type hints обязательны
def execute_step(step: PlanStep, state: EpisodeState) -> VerifiedFact:
    ...

# Docstrings Google style
def validate_truth_boundary(text: str, facts: List[VerifiedFact]) -> ValidationResult:
    """Validate that all numbers in text are backed by VerifiedFacts.

    Args:
        text: LLM-generated report text
        facts: Available verified facts

    Returns:
        ValidationResult with verdict (PASS/BLOCK) and issues

    Raises:
        ValueError: If text is empty
    """
```

### Testing Conventions
```python
# Test naming: test_<component>_<scenario>_<expected>
def test_truth_gate_blocks_unverified_numbers():
    ...

def test_temporal_integrity_allows_fact_with_correct_lag():
    ...

# Fixtures в conftest.py
@pytest.fixture
def sample_episode():
    return EpisodeState(
        episode_id=uuid4(),
        asof_timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
        user_id="test_user"
    )

# Мокирование внешних API обязательно
@patch('yfinance.download')
def test_yfinance_adapter_handles_missing_data(mock_download):
    mock_download.return_value = None
    result = YFinanceAdapter().fetch_ohlcv("INVALID")
    assert result.status == "error"
```

---

## Error Handling Patterns

### Graceful Degradation
```python
def fetch_data_with_fallback(symbol: str) -> Optional[pd.DataFrame]:
    """Try primary source, fallback to secondary, fail gracefully."""
    try:
        return yfinance.download(symbol, period="30d")
    except Exception as e:
        logger.warning(f"YFinance failed for {symbol}: {e}, trying cache")
        try:
            return redis_cache.get(f"ohlcv:{symbol}")
        except Exception as e2:
            logger.error(f"Cache also failed: {e2}")
            return None  # Fail gracefully, don't crash
```

### Fail-Fast для критичных компонентов
```python
def validate_sandbox_isolation():
    """Pre-flight check: sandbox must be isolated or crash."""
    try:
        # Attempt to access host filesystem from sandbox
        result = docker_exec(container, "ls /host")
        if result.returncode == 0:
            raise SecurityViolation("Sandbox can access host filesystem!")
    except docker.errors.APIError:
        pass  # Expected — sandbox is isolated, good
```

---

## Performance Patterns

### Caching Strategy
```python
# Level 1: In-memory (per-request)
@lru_cache(maxsize=128)
def parse_investigation_plan(plan_json: str) -> InvestigationPlan:
    return InvestigationPlan.parse_raw(plan_json)

# Level 2: Redis (cross-request, short TTL)
def get_market_data(symbol: str, date: str) -> pd.DataFrame:
    key = f"market:{symbol}:{date}"
    cached = redis.get(key)
    if cached:
        return pickle.loads(cached)

    data = yfinance.download(symbol, start=date, end=date)
    redis.setex(key, timedelta(hours=1), pickle.dumps(data))
    return data

# Level 3: Neo4j (persistent, invalidate on new episode)
def get_verified_fact(fact_id: UUID) -> VerifiedFact:
    # Facts are immutable, cache forever
    return neo4j.query("MATCH (f:VerifiedFact {id: $id}) RETURN f", id=fact_id)
```

### Parallel Execution
```python
# Multi-agent debate параллельно
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(run_agent, "Bull", evidence): "Bull",
        executor.submit(run_agent, "Bear", evidence): "Bear",
        executor.submit(run_agent, "Quant", evidence): "Quant",
    }
    reports = [future.result() for future in as_completed(futures)]
```

---

## Security Patterns

### Secrets Management
```python
# ❌ BAD
API_KEY = "sk-1234567890abcdef"

# ✅ GOOD
from os import environ
API_KEY = environ.get("FRED_API_KEY")
if not API_KEY:
    raise ValueError("FRED_API_KEY environment variable not set")

# Docker Compose
services:
  app:
    environment:
      - FRED_API_KEY=${FRED_API_KEY}  # Injected from .env file
```

### Input Validation
```python
from pydantic import BaseModel, validator

class QueryRequest(BaseModel):
    query: str
    asof_timestamp: datetime

    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long (max 1000 chars)')
        return v

    @validator('asof_timestamp')
    def asof_must_be_past(cls, v):
        if v > datetime.now(timezone.utc):
            raise ValueError('asof_timestamp cannot be in the future')
        return v
```

---

## Logging \& Observability

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

# ❌ BAD
print(f"Processing query: {query}")

# ✅ GOOD
logger.info(
    "query_processing_started",
    episode_id=episode_id,
    query_length=len(query),
    asof_timestamp=asof_timestamp.isoformat()
)
```

### Metrics (Prometheus)
```python
from prometheus_client import Counter, Histogram

# Counters
queries_total = Counter('ape_queries_total', 'Total queries processed')
hallucinations_total = Counter('ape_hallucinations_total', 'Hallucinations detected')

# Histograms
query_duration = Histogram('ape_query_duration_seconds', 'Query processing time')

# Usage
@query_duration.time()
def process_query(query: str) -> Report:
    queries_total.inc()
    ...
    if hallucination_detected:
        hallucinations_total.inc()
```

---

*Этот файл обновляется при появлении новых архитектурных паттернов*
*Last Updated: 2026-02-07*
