# 📋 Техническое задание по улучшению APE 2026

**Основа:** Комплексная оценка проекта (Claude Opus 4.6 Audit)
**Текущая оценка:** 6.1/10
**Целевая оценка:** 8.5/10 (Production-Ready)
**Срок реализации:** 4 недели (Week 11-14)
**Приоритизация:** MoSCoW (Must/Should/Could/Won't)

---

## 🎯 Стратегические цели

1. **Превратить прототип в работающий продукт** - реализовать все заглушки
2. **Устранить юридические риски** - compliance и disclaimers
3. **Достичь production-readiness** - real integration tests, monitoring, performance
4. **Снизить technical debt** - рефакторинг God Objects, добавить миграции
5. **Подготовить к масштабированию** - async, auto-scaling, cost tracking

---

## 📊 Текущее состояние vs Целевое

| Категория | Текущая оценка | Целевая | Дельта | Приоритет |
|-----------|----------------|---------|--------|-----------|
| ML/AI Pipeline | 5/10 | 9/10 | +4 | 🔴 CRITICAL |
| Бизнес/Compliance | 2/10 | 8/10 | +6 | 🔴 CRITICAL |
| Производительность | 5/10 | 8/10 | +3 | 🟡 HIGH |
| Тестирование | 7/10 | 9/10 | +2 | 🟡 HIGH |
| Безопасность | 6/10 | 8/10 | +2 | 🟡 HIGH |
| Наблюдаемость | 6/10 | 8/10 | +2 | 🟢 MEDIUM |
| Frontend/UX | 6/10 | 8/10 | +2 | 🟢 MEDIUM |
| Данные и БД | 7/10 | 9/10 | +2 | 🟢 MEDIUM |
| Архитектура | 7/10 | 9/10 | +2 | 🟢 MEDIUM |
| **ОБЩАЯ** | **6.1/10** | **8.5/10** | **+2.4** | - |

---

## 🔴 PHASE 1: CRITICAL FIXES (Week 11) — Must Have

**Цель:** Устранить show-stoppers, которые блокируют production deployment

### 1.1 LLM Integration (ML/AI Pipeline: 5→9)

**Статус:** ✅ **ЧАСТИЧНО COMPLETE** (Week 11 Day 1)
- ✅ OpenAI integration реализован
- ✅ Gemini integration реализован
- ✅ DeepSeek integration реализован
- ✅ Cost tracking добавлен
- ⏳ Требуется: интеграция с orchestrator

**Задачи:**

#### 1.1.1 Интеграция LLM провайдеров с оркестратором
**Приоритет:** 🔴 CRITICAL
**Effort:** M (3 дня)
**Owner:** Backend Team

**Описание:**
Интегрировать реализованные LLM провайдеры (OpenAI, Gemini, DeepSeek) в `DebateNode` оркестратора вместо mock-провайдера.

**Acceptance Criteria:**
- [ ] `DebateNode` использует реальные LLM провайдеры по умолчанию
- [ ] Конфигурация провайдера через environment variables (`LLM_PROVIDER=openai|gemini|deepseek`)
- [ ] Fallback на mock только в test environment
- [ ] Retry logic с exponential backoff для API failures
- [ ] Circuit breaker для защиты от API outages
- [ ] Cost tracking логируется в БД (new table: `llm_api_usage`)

**Технические требования:**
```python
# src/orchestration/nodes/debate_node.py
class DebateNode:
    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", "deepseek")  # Default to cheapest
        self.llm_client = LLMDebateNode(provider=provider)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )

    async def execute(self, state: GraphState) -> GraphState:
        try:
            with self.circuit_breaker:
                result = await self.llm_client.generate_debate_async(fact)
                await self._log_cost(result.cost)
        except CircuitBreakerOpen:
            # Fallback to cached/simplified response
            logger.error("LLM circuit breaker open, using fallback")
```

**Файлы:**
- `src/orchestration/nodes/debate_node.py` (modify)
- `src/storage/timescale_client.py` (add llm_api_usage table)
- `tests/integration/test_debate_node_real_llm.py` (new)

---

#### 1.1.2 Async LLM Calls
**Приоритет:** 🔴 CRITICAL
**Effort:** M (2 дня)

**Описание:**
Конвертировать синхронные LLM вызовы в async для предотвращения blocking.

**Acceptance Criteria:**
- [ ] `_call_openai`, `_call_gemini`, `_call_deepseek` конвертированы в async
- [ ] Используется `httpx.AsyncClient` вместо синхронных клиентов
- [ ] Timeout configuration per provider (default: 30s)
- [ ] Concurrent debates для нескольких фактов (asyncio.gather)
- [ ] Benchmark: 3 debates параллельно < 10s (vs 30s sequential)

**Пример:**
```python
async def _call_openai_async(self, prompt: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={...}
        )
```

---

#### 1.1.3 Prompt Versioning
**Приоритет:** 🟡 HIGH
**Effort:** S (1 день)

**Описание:**
Система версионирования промптов для A/B тестинга и rollback.

**Acceptance Criteria:**
- [ ] Промпты хранятся в `prompts/` директории с версиями
- [ ] Формат: `prompts/debate/sharpe_ratio_v1.txt`, `v2.txt`
- [ ] Конфигурация активной версии в environment (`PROMPT_VERSION=v2`)
- [ ] A/B testing: 50/50 split между v1 и v2 для сравнения
- [ ] Metrics: accuracy, cost, latency per prompt version

---

### 1.2 Compliance & Legal (Бизнес/Compliance: 2→8)

**Приоритет:** 🔴 CRITICAL (юридический риск)
**Effort:** S (2 дня)

#### 1.2.1 Disclaimer Integration
**Acceptance Criteria:**
- [ ] **API Response Disclaimer:**
  ```json
  {
    "result": {...},
    "disclaimer": "This analysis is for informational purposes only and does not constitute investment advice. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions.",
    "data_sources": ["Yahoo Finance", "LLM: DeepSeek"],
    "generated_at": "2026-02-08T12:34:56Z"
  }
  ```
- [ ] **Frontend UI Disclaimer:**
  - Footer на всех страницах
  - Modal при первом входе (accepted via checkbox, stored in localStorage)
  - Disclaimer banner на странице results
- [ ] **Email/Export Disclaimer:**
  - Включить в PDF/CSV экспорты
  - Email footer
- [ ] **Terms of Service page** (`/terms`)
- [ ] **Privacy Policy page** (`/privacy`)

**Файлы:**
- `src/api/schemas.py` (add disclaimer field to all response models)
- `src/api/middleware/disclaimer_middleware.py` (new)
- `frontend/components/layout/Footer.tsx` (update)
- `frontend/components/DisclaimerModal.tsx` (new)
- `frontend/app/terms/page.tsx` (new)
- `frontend/app/privacy/page.tsx` (new)

---

#### 1.2.2 Immutable Audit Trail
**Acceptance Criteria:**
- [ ] All user queries logged to **WORM storage** (Write-Once-Read-Many)
- [ ] Log format:
  ```json
  {
    "query_id": "uuid",
    "user_id": "api_key_hash",
    "timestamp": "ISO8601",
    "query": "text",
    "results": {...},
    "llm_provider": "deepseek",
    "cost": 0.000264,
    "ip_address": "hashed",
    "user_agent": "string"
  }
  ```
- [ ] Retention policy: 7 years (financial compliance standard)
- [ ] Encryption at rest (AES-256)
- [ ] Tamper detection: cryptographic hash chain
- [ ] Export API для compliance audits

**Технология:**
- TimescaleDB с continuous aggregates для WORM-like behavior
- Или AWS S3 с Object Lock (compliance mode)

**Файлы:**
- `src/storage/audit_trail.py` (new)
- `src/api/middleware/audit_middleware.py` (new)

---

#### 1.2.3 Data Source Attribution
**Acceptance Criteria:**
- [ ] Каждый факт включает `source` field:
  ```python
  {
    "statement": "AAPL Sharpe ratio is 1.95",
    "value": 1.95,
    "source": "Yahoo Finance",
    "source_url": "https://finance.yahoo.com/quote/AAPL",
    "fetched_at": "2026-02-08T10:00:00Z",
    "verified": true
  }
  ```
- [ ] UI отображает source как hyperlink
- [ ] API endpoint `/api/v1/sources` для списка всех data sources

---

### 1.3 Cost Tracking & Unit Economics (Бизнес/Compliance: 2→8)

**Приоритет:** 🔴 CRITICAL
**Effort:** S (1 день)

#### 1.3.1 Per-Query Cost Tracking
**Acceptance Criteria:**
- [ ] Middleware логирует cost для каждого query
- [ ] Cost breakdown:
  - LLM API cost (OpenAI/Gemini/DeepSeek)
  - Data fetching cost (if applicable)
  - Compute cost (estimation based on execution time)
- [ ] Dashboard в Grafana:
  - Cost per day/week/month
  - Cost per user
  - Cost per LLM provider
  - Average cost per query
- [ ] Alerting при превышении budget ($100/day)

**Файлы:**
- `src/api/middleware/cost_tracking_middleware.py` (new)
- `src/storage/timescale_client.py` (add query_costs table)
- `grafana/dashboards/cost_dashboard.json` (new)

---

#### 1.3.2 Unit Economics Model
**Acceptance Criteria:**
- [ ] Документ `docs/UNIT_ECONOMICS.md`:
  ```
  Cost per Query:
    - LLM API (DeepSeek): $0.000264
    - Data fetching: $0.00001
    - Infrastructure: $0.00005
    - Total: $0.000324

  Revenue per Query (hypothetical):
    - Free tier: $0 (limit: 100 queries/month)
    - Pro tier: $0.01 per query
    - Margin: $0.00968 (96.8%)

  Break-even: 10,340 Pro queries/month at $5K infrastructure cost
  ```
- [ ] Pricing calculator: `scripts/pricing_calculator.py`

---

### 1.4 Real Integration Tests (Тестирование: 7→9)

**Приоритет:** 🔴 CRITICAL
**Effort:** M (3 дня)

#### 1.4.1 Golden Set с реальными LLM
**Acceptance Criteria:**
- [ ] Прогнать все 30 Golden Set queries через реальный LLM (DeepSeek)
- [ ] Зафиксировать baseline метрики:
  - Accuracy: ≥90% (within tolerance)
  - Hallucination rate: 0%
  - Temporal compliance: 100%
- [ ] Результаты в `tests/golden_set/results/baseline_deepseek_2026_02_08.json`
- [ ] CI/CD: регрессионный тест раз в неделю

**Команда:**
```bash
pytest tests/integration/test_golden_set_production.py \
  --llm-provider=deepseek \
  --save-baseline \
  -m real_llm
```

---

#### 1.4.2 End-to-End Pipeline Test
**Acceptance Criteria:**
- [ ] Один E2E тест прогоняет query через весь pipeline:
  - User query → PLAN (real Claude) → VEE → GATE → DEBATE (real LLM) → Response
- [ ] Validates:
  - All pipeline steps execute
  - No hallucinations detected
  - Response includes disclaimer
  - Cost logged correctly
  - Audit trail created
- [ ] Время выполнения: < 30s

**Файл:** `tests/integration/test_e2e_real_llm.py`

---

## 🟡 PHASE 2: HIGH PRIORITY (Week 12) — Should Have

**Цель:** Улучшить производительность, observability, архитектуру

### 2.1 Performance & Scalability (Производительность: 5→8)

#### 2.1.1 Load Testing & Benchmarking
**Effort:** M (2 дня)

**Acceptance Criteria:**
- [ ] Запустить Locust load test (уже создан в Week 9 Day 5):
  ```bash
  locust -f tests/performance/locustfile.py \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --html reports/load_test_2026_02_15.html
  ```
- [ ] Зафиксировать baseline metrics:
  - RPS (Requests Per Second): target ≥10
  - P95 latency: < 5s
  - P99 latency: < 10s
  - Success rate: ≥95%
  - Concurrent users: 100
- [ ] Результаты в `tests/performance/results/`
- [ ] CI/CD: performance regression test на каждый PR

---

#### 2.1.2 Async Orchestrator
**Effort:** L (5 дней)

**Описание:**
Конвертировать синхронный `LangGraphOrchestrator` в async для устранения blocking.

**Acceptance Criteria:**
- [ ] `LangGraphOrchestrator.execute()` → `async execute()`
- [ ] Все nodes (PLAN, FETCH, VEE, GATE, DEBATE) async
- [ ] Background task queue (Celery или FastAPI BackgroundTasks)
- [ ] WebSocket для real-time progress updates
- [ ] Benchmark: 10x improvement в throughput

---

#### 2.1.3 Auto-Scaling (HPA)
**Effort:** S (1 день)

**Acceptance Criteria:**
- [ ] Kubernetes HorizontalPodAutoscaler:
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: ape-api
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: ape-api
    minReplicas: 2
    maxReplicas: 20
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  ```
- [ ] Stress test: автоматическое масштабирование от 2 до 20 pods

---

### 2.2 Observability (Наблюдаемость: 6→8)

#### 2.2.1 Distributed Tracing
**Effort:** M (2 дня)

**Acceptance Criteria:**
- [ ] OpenTelemetry integration
- [ ] Jaeger backend для визуализации traces
- [ ] Trace каждого query через весь pipeline (PLAN → VEE → GATE → DEBATE)
- [ ] Custom spans для:
  - LLM API calls (with latency breakdown)
  - Database queries
  - VEE code execution
  - Cache hits/misses
- [ ] Trace sampling: 10% в production (100% в dev)

**Пример trace:**
```
Query abc123 (total: 8.2s)
├─ PLAN node (2.1s)
│  └─ Claude API call (1.9s)
├─ FETCH node (0.3s)
│  └─ yfinance API call (0.2s)
├─ VEE node (1.8s)
│  └─ Docker exec (1.6s)
├─ GATE node (0.5s)
└─ DEBATE node (3.5s)
   └─ DeepSeek API call (3.3s)
```

---

#### 2.2.2 Alerting
**Effort:** S (1 день)

**Acceptance Criteria:**
- [ ] Alertmanager для Prometheus
- [ ] Alert rules:
  - API error rate > 5% (5min window)
  - P95 latency > 10s
  - LLM cost > $100/day
  - Memory usage > 90%
  - Disk usage > 80%
- [ ] Каналы: Slack, Email, PagerDuty (опционально)

---

### 2.3 Architecture Refactoring (Архитектура: 7→9)

#### 2.3.1 Разбить main.py на Routers
**Effort:** S (2 дня)

**Описание:**
Устранить God Object (947 LOC) путем разделения на FastAPI routers.

**Acceptance Criteria:**
- [ ] Структура:
  ```
  src/api/
  ├── main.py (100 LOC max - только app init)
  ├── routers/
  │   ├── __init__.py
  │   ├── query.py (submit_query, get_status)
  │   ├── episodes.py (get_episode)
  │   ├── facts.py (get_facts)
  │   ├── health.py (health, metrics)
  │   └── admin.py (admin endpoints)
  ├── dependencies.py (shared dependencies)
  └── middleware/ (existing)
  ```
- [ ] Каждый router < 200 LOC
- [ ] Все тесты проходят без изменений

---

#### 2.3.2 WebSocket State в Redis
**Effort:** M (2 дня)

**Описание:**
Переместить `ConnectionManager` state из памяти в Redis Pub/Sub для stateless deployment.

**Acceptance Criteria:**
- [ ] WebSocket subscriptions хранятся в Redis:
  ```python
  # Key: ws:query:{query_id}
  # Value: Set of connection IDs
  ```
- [ ] Pub/Sub для broadcast updates:
  ```python
  await redis.publish(
      f"ws:query:{query_id}",
      json.dumps({"type": "status", "data": {...}})
  )
  ```
- [ ] При restart pod'а соединения сохраняются (reconnect)
- [ ] Load test: 1000 concurrent WebSocket connections

---

### 2.4 Database Migrations (Данные и БД: 7→9)

#### 2.4.1 Alembic Integration
**Effort:** S (1 день)

**Acceptance Criteria:**
- [ ] Установка: `pip install alembic`
- [ ] Инициализация: `alembic init alembic`
- [ ] Миграция существующих init_scripts в Alembic:
  ```
  alembic/versions/
  ├── 001_create_verified_facts_table.py
  ├── 002_create_episodes_table.py
  ├── 003_create_query_costs_table.py
  └── 004_create_llm_api_usage_table.py
  ```
- [ ] CI/CD: автоматический `alembic upgrade head` при deploy
- [ ] Rollback процедура в runbook

---

## 🟢 PHASE 3: MEDIUM PRIORITY (Week 13) — Could Have

**Цель:** Улучшить UX, безопасность, тестирование

### 3.1 Frontend E2E Tests (Frontend/UX: 6→8)

#### 3.1.1 Playwright Integration
**Effort:** M (3 дня)

**Acceptance Criteria:**
- [ ] Установка: `npm install -D @playwright/test`
- [ ] Config: `playwright.config.ts`
- [ ] E2E тесты (минимум 10):
  1. User login flow
  2. Submit query
  3. View query status (pipeline animation)
  4. View results (facts table)
  5. Debate perspectives
  6. Export CSV/JSON
  7. Chart interactions
  8. Disclaimer modal
  9. Error handling (invalid query)
  10. Mobile responsiveness
- [ ] CI/CD: запуск на каждый PR (headless mode)
- [ ] Visual regression testing (Percy или Chromatic)

**Команда:**
```bash
npx playwright test
npx playwright test --ui  # Interactive mode
```

---

### 3.2 Security Enhancements (Безопасность: 6→8)

#### 3.2.1 Penetration Testing
**Effort:** M (external contractor, 1 week)

**Acceptance Criteria:**
- [ ] OWASP Top 10 тестирование
- [ ] VEE Sandbox security review (container escape, privilege escalation)
- [ ] API rate limiting bypass attempts
- [ ] SQL injection, XSS, CSRF тесты
- [ ] Отчет с приоритизацией уязвимостей
- [ ] Remediation план

---

#### 3.2.2 JWT для Frontend Sessions
**Effort:** S (2 дня)

**Acceptance Criteria:**
- [ ] JWT вместо API keys для frontend auth
- [ ] Refresh token mechanism
- [ ] Expiration: Access token 15min, Refresh token 7 days
- [ ] Secure cookie storage (httpOnly, secure, sameSite)

---

### 3.3 ML/AI Enhancements (ML/AI Pipeline: 9→9)

#### 3.3.1 MLflow/W&B Integration
**Effort:** M (3 дня)

**Acceptance Criteria:**
- [ ] MLflow tracking для:
  - Prompt versions
  - LLM provider comparisons
  - Golden Set accuracy metrics
  - Cost per experiment
- [ ] UI для просмотра экспериментов: `http://localhost:5000`

---

#### 3.3.2 Data/Concept Drift Detection
**Effort:** M (3 дня)

**Acceptance Criteria:**
- [ ] Мониторинг изменений в:
  - Input query distribution (topic shift)
  - LLM response patterns
  - Accuracy degradation over time
- [ ] Alert при drift > 10% от baseline
- [ ] Weekly drift report

---

## ⚪ PHASE 4: LOW PRIORITY (Week 14) — Won't Have (для v1.0)

**Цель:** Nice-to-have features для будущих версий

### 4.1 Advanced Features
- Paper trading для верификации рекомендаций
- A/B testing infrastructure (feature flags)
- CDN для frontend static assets
- Canary deployments
- Multi-region deployment
- GraphQL API (в дополнение к REST)
- Mobile app (React Native)

---

## 📅 Подробный план по неделям

### Week 11: CRITICAL FIXES (Feb 11-17)
**Цель:** Устранить show-stoppers

| Day | Задача | Effort | Owner |
|-----|--------|--------|-------|
| Mon | 1.1.1 LLM Orchestrator Integration | M | Backend |
| Tue | 1.1.1 (continue) + 1.1.2 Async LLM | M | Backend |
| Wed | 1.2.1 Disclaimer Integration | S | Full-stack |
| Thu | 1.3.1 Cost Tracking Middleware | S | Backend |
| Fri | 1.4.1 Golden Set Real LLM | M | QA |

**Week 11 Deliverables:**
- ✅ Real LLM integrated with orchestrator
- ✅ Disclaimer в UI и API
- ✅ Cost tracking operational
- ✅ Golden Set baseline established

---

### Week 12: PERFORMANCE & OBSERVABILITY (Feb 18-24)

| Day | Задача | Effort | Owner |
|-----|--------|--------|-------|
| Mon | 2.1.1 Load Testing | M | DevOps |
| Tue | 2.1.2 Async Orchestrator (start) | L | Backend |
| Wed | 2.1.2 Async Orchestrator (continue) | L | Backend |
| Thu | 2.2.1 Distributed Tracing | M | DevOps |
| Fri | 2.3.1 Refactor main.py | S | Backend |

**Week 12 Deliverables:**
- ✅ Load test baseline
- ✅ Async pipeline operational
- ✅ Distributed tracing working
- ✅ main.py refactored

---

### Week 13: UX & SECURITY (Feb 25 - Mar 3)

| Day | Задача | Effort | Owner |
|-----|--------|--------|-------|
| Mon | 3.1.1 Playwright Setup | M | Frontend |
| Tue | 3.1.1 E2E Tests (10 tests) | M | Frontend |
| Wed | 3.2.2 JWT Integration | S | Full-stack |
| Thu | 2.4.1 Alembic Migrations | S | Backend |
| Fri | Buffer для bug fixes | - | All |

**Week 13 Deliverables:**
- ✅ E2E tests passing
- ✅ JWT authentication
- ✅ Alembic migrations

---

### Week 14: POLISH & VALIDATION (Mar 4-10)

| Day | Задача | Effort | Owner |
|-----|--------|--------|-------|
| Mon | 1.2.2 Audit Trail | M | Backend |
| Tue | 2.2.2 Alerting | S | DevOps |
| Wed | 2.3.2 Redis WebSocket | M | Backend |
| Thu | 1.4.2 E2E Pipeline Test | M | QA |
| Fri | Final validation + docs | - | All |

**Week 14 Deliverables:**
- ✅ Audit trail immutable
- ✅ Alerts configured
- ✅ WebSocket stateless
- ✅ Full E2E test passing

---

## 📈 Прогнозируемая итоговая оценка

| Категория | До | После | Комментарий |
|-----------|-----|-------|-------------|
| ML/AI Pipeline | 5 | **9** | Real LLM + MLflow + drift detection |
| Бизнес/Compliance | 2 | **8** | Disclaimer + audit trail + cost tracking |
| Производительность | 5 | **8** | Async + load tests + auto-scaling |
| Тестирование | 7 | **9** | E2E + real LLM tests + 95% coverage |
| Безопасность | 6 | **8** | Pentest + JWT + hardening |
| Наблюдаемость | 6 | **8** | Distributed tracing + alerting |
| Frontend/UX | 6 | **8** | E2E tests + UX improvements |
| Данные и БД | 7 | **9** | Alembic + optimizations |
| Архитектура | 7 | **9** | Refactoring + async + stateless |
| Документация | 9 | **9** | Maintain excellence |
| **ОБЩАЯ** | **6.1** | **8.5** | **Production-Ready ✅** |

---

## 🎯 Success Metrics (Definition of Done)

### Technical Metrics
- [ ] **Test Coverage:** ≥95% (pytest --cov-fail-under=95)
- [ ] **Golden Set Accuracy:** ≥90%
- [ ] **Hallucination Rate:** 0%
- [ ] **Load Test:** 100 concurrent users, P95 < 5s, Success ≥95%
- [ ] **E2E Tests:** 10+ passing Playwright tests
- [ ] **Security:** 0 critical vulnerabilities (pentest)
- [ ] **Cost per Query:** < $0.001 (with DeepSeek)

### Business Metrics
- [ ] **Compliance:** Disclaimer в 100% responses
- [ ] **Audit Trail:** 100% queries logged immutably
- [ ] **Uptime:** 99.9% (monitored)
- [ ] **Break-even:** Unit economics модель утверждена

### Operational Metrics
- [ ] **Deployment:** CI/CD pipeline без ручных шагов
- [ ] **Monitoring:** 0 blind spots (full tracing)
- [ ] **Alerting:** 100% critical events alerted
- [ ] **Documentation:** Runbooks для всех critical scenarios

---

## 🚨 Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM API outages | High | High | Circuit breaker + fallback + caching |
| Cost overrun | Medium | High | Cost tracking + daily budget alerts |
| Performance degradation | Medium | High | Load testing before each release |
| Security breach | Low | Critical | Pentest + security review + monitoring |
| Bus factor = 1 | High | High | Comprehensive documentation + code reviews (AI) |

---

## 📚 Dependencies

### External
- [ ] Penetration testing contractor (Week 13)
- [ ] Legal review of disclaimer text (Week 11)
- [ ] Budget approval для LLM API costs ($500/month estimated)

### Internal
- [ ] Week 11 Day 1 COMPLETE ✅ (LLM integration реализован)
- [ ] API keys configured: OpenAI, Gemini, DeepSeek ✅
- [ ] Infrastructure running: TimescaleDB, Neo4j, Redis ✅

---

## 📝 Out of Scope (для v1.0)

- Multi-language support (только English)
- Mobile app
- Multi-tenancy (single-tenant для v1.0)
- Custom ML models (только LLM API)
- Real-time market data (только historical data)
- Trading execution (read-only analysis only)

---

## 🎓 Learning & Knowledge Transfer

**Документация для Bus Factor Mitigation:**
- [ ] Architecture Decision Records (ADR) для всех major decisions
- [ ] Runbooks для critical procedures
- [ ] Video walkthrough проекта (30 min)
- [ ] Onboarding guide для новых разработчиков
- [ ] Weekly summary продолжать в `docs/weekly_summaries/`

---

## ✅ Acceptance Process

### Code Review
- [ ] Все PR require review (даже от AI)
- [ ] Automated checks: lint, test, security scan
- [ ] Manual review: architecture, business logic

### QA Process
- [ ] Unit tests pass (pytest)
- [ ] Integration tests pass (with real APIs)
- [ ] E2E tests pass (Playwright)
- [ ] Load test baseline maintained
- [ ] Security scan clean

### Deployment Approval
- [ ] Staging environment validation
- [ ] Blue-green deployment готово к rollback
- [ ] Monitoring dashboards configured
- [ ] Runbook updated

---

## 📞 Stakeholders

| Role | Responsibility | Contact |
|------|----------------|---------|
| Product Owner | Prioritization, acceptance | - |
| Tech Lead | Architecture, code review | Solo dev |
| QA | Test strategy, Golden Set | Solo dev |
| DevOps | Infrastructure, monitoring | Solo dev |
| Legal | Disclaimer approval | External |
| Security | Pentest, review | External |

---

## 🏁 Final Checklist

Перед объявлением Production-Ready:

### Technical
- [ ] All PHASE 1 tasks complete (Week 11)
- [ ] All PHASE 2 tasks complete (Week 12)
- [ ] Load test passed
- [ ] Security pentest passed
- [ ] E2E tests passing
- [ ] Monitoring & alerting operational

### Business
- [ ] Legal disclaimer approved
- [ ] Unit economics validated
- [ ] Pricing strategy approved
- [ ] Terms of Service published
- [ ] Privacy Policy published

### Operational
- [ ] Runbooks complete
- [ ] On-call rotation defined (even if solo)
- [ ] Incident response plan
- [ ] Backup & restore tested
- [ ] Disaster recovery plan

---

**Version:** 1.0
**Created:** 2026-02-08
**Based on:** Claude Opus 4.6 Comprehensive Evaluation
**Next Review:** After Week 11 completion
**Estimated Completion:** 2026-03-10 (4 weeks)

---

> **Note:** Этот документ — живой артефакт. Обновлять после каждой недели с фактическим прогрессом и уточнениями.
