# CLAUDE.md — APE 2026 Root Anchor

**Версия:** 0.9.3 (Week 9 Day 3 - Golden Set Validation)
**Дата:** 2026-02-09
**Статус:** MVP Complete → Production Baseline Validation

---

## 📌 Project Identity

**Name:** APE 2026 (Autonomous Prediction Engine)
**Type:** Financial Decision Support System (Read-Only, Non-Trading)
**Mission:** Финансовая аналитика с математической гарантией zero hallucination

**Elevator Pitch:**
> Система, которая никогда не врет уверенно. LLM генерирует код, а не числа. Все выводы проверяемы математически. Fail-closed при неопределенности.

---

## 🎯 North Star Metrics (Блокирующие)

| Метрика | Целевое значение | Статус |
|---------|------------------|--------|
| **Hallucination Rate (Numerical)** | 0.00% | 🟢 Ready (Golden Set validation framework) |
| **Temporal Adherence** | 100% | 🟢 Enforced (TIM + Golden Set) |
| **Calibration Error (ECE)** | < 0.05 | 🟡 In Progress (Week 9 Day 4) |
| **Evidence Coverage** | ≥ 90% | 🟢 Achieved (Debate + Synthesis) |

---

## 🏗️ Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                      │
│  (FastAPI + WebSocket для streaming, React Frontend)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER (LangGraph)                 │
│  State Machine: PLAN → EXECUTE → DEBATE → VALIDATE          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────┬──────────────┬──────────────┬───────────────┐
│  REASONING   │   EXECUTION  │   VALIDATION │    MEMORY     │
│    LAYER     │    LAYER     │    LAYER     │    LAYER      │
│              │              │              │               │
│ DeepSeek-R1  │  VEE         │ Truth Gate   │  Neo4j        │
│ Claude 3.7   │  (Sandbox)   │ Doubter      │  ClickHouse   │
│ GPT-4.5      │  Adapters    │ Sensitivity  │  Qdrant       │
└──────────────┴──────────────┴──────────────┴───────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                               │
│  External APIs (FRED, YF) + Internal DBs                     │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. **Truth Boundary Gate** (Уникальная особенность)
- **Принцип:** LLM ЗАПРЕЩЕНО генерировать числа напрямую
- **Enforcement:** Все числа извлекаются через VEE execution → VerifiedFact
- **Validation:** Детерминированная проверка: text_numbers ⊆ verified_facts

#### 2. **VEE (Verifiable Execution Environment)**
- Docker sandbox с изоляцией (network whitelist, filesystem restrictions)
- Timeout 60 sec, memory limit 2GB
- Pre-execution safety checks (no eval, no os.system, etc.)

#### 3. **Temporal Integrity Module** (Финансовая специфика)
- Отслеживает `asof_timestamp` + `publication_lag` для каждого факта
- Блокирует look-ahead bias (использование будущих данных в прошлом)
- Критично для backtesting и historical analysis

#### 4. **Multi-Agent Debate** (Adversarial Reasoning)
- Bull (optimistic), Bear (pessimistic), Quant (neutral)
- Параллельное исполнение → vote entropy → consensus
- Doubter agent пытается опровергнуть финальный отчет

#### 5. **Sensitivity Harness**
- Parameter sweeps (window, method, outliers)
- Sign flip detection (15.3% → -2.1% = критично)
- Confidence penalty при нестабильности

---

## 🛠️ Tech Stack

| Компонент | Технология | Версия | Решение |
|-----------|------------|--------|---------|
| **Orchestration** | LangGraph | >=0.2.0 | ✅ Принято (ADR-001) |
| **Language** | Python | 3.11+ | ✅ |
| **Reasoning Model** | DeepSeek-R1 | Latest | 🟡 Предложено (ADR-002) |
| **Validation Model** | Claude Sonnet 4.5 | Latest | ✅ |
| **Debate Models** | DeepSeek-V3 | Latest | ✅ |
| **Sandbox** | Docker | >=24.0 | ✅ Принято (ADR-003) |
| **Graph DB** | Neo4j | >=5.14 | ✅ Принято (ADR-004) |
| **Time-Series** | TBD | - | 🔴 Требует решения (ADR-005) |
| **Vector DB** | TBD | - | 🔴 Требует решения (ADR-006) |

**Open Decisions (блокируют Week 1):**
- ADR-005: ClickHouse vs Postgres+TimescaleDB vs DuckDB
- ADR-006: Qdrant vs ChromaDB vs pgvector

---

## 📂 Project Structure

```
E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\
├── CLAUDE.md                     # ← Этот файл (Root Anchor)
├── ТЕХНИЧЕСКОЕ ЗАДАНИЕ_*.md      # Полное ТЗ v2.1 (1860 строк)
├── Методология создания проекта.txt
├── .cursor/
│   ├── rules/                    # Правила поведения Claude
│   │   ├── 00-general.mdc        # No yapping, completeness, style
│   │   ├── 05-security.mdc       # VEE, secrets, CoT prohibition
│   │   └── 20-testing.mdc        # TDD workflow, coverage
│   └── memory_bank/              # Persistent context
│       ├── projectbrief.md       # Суть проекта, цели
│       ├── activeContext.md      # Текущий фокус, блокеры
│       ├── systemPatterns.md     # Архитектурные паттерны
│       ├── progress.md           # Трекер задач
│       └── decisions.md          # ADR журнал (9 решений)
└── ape-2026/                     # ← Код (будет создан в Week 1)
    ├── README.md
    ├── requirements.txt
    ├── docker-compose.yml
    ├── .env.example
    ├── src/
    │   ├── orchestration/
    │   │   ├── langgraph_workflow.py
    │   │   └── nodes/           # PLAN, EXECUTE, DEBATE, VALIDATE, etc.
    │   ├── vee/
    │   │   ├── sandbox_runner.py
    │   │   ├── adapters/        # YFinance, FRED, Neo4j, ClickHouse
    │   │   └── safety_checks.py
    │   ├── validators/
    │   │   ├── truth_boundary.py
    │   │   ├── temporal_integrity.py
    │   │   └── sensitivity_harness.py
    │   ├── models/
    │   │   ├── artifacts.py     # Pydantic schemas
    │   │   └── prompts/
    │   ├── storage/
    │   │   ├── neo4j_client.py
    │   │   └── clickhouse_client.py  # or timescaledb_client.py
    │   └── api/
    │       └── main.py          # FastAPI app
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   └── e2e/
    ├── eval/
    │   ├── task_suite.json      # 100 задач для validation
    │   └── run_eval.py
    └── deployment/
        ├── Dockerfile
        └── docker-compose.yml
```

---

## 🚀 Commands (для быстрого старта)

### Development
```bash
# Setup environment
cd ape-2026
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start infrastructure
docker-compose up -d  # Neo4j, ClickHouse, Qdrant

# Run tests
pytest tests/unit                  # Fast (<10 sec)
pytest tests/integration           # Slower (minutes)
pytest tests/e2e -m e2e            # Full pipeline (10+ min)

# Run linters
black src/ tests/ --check
ruff check src/ tests/
mypy src/

# Run application (после реализации)
uvicorn src.api.main:app --reload
```

### Memory Bank Updates
```bash
# После каждой сессии
# 1. Update activeContext.md (что сделали, следующий шаг)
# 2. Update progress.md (отметить выполненные [x])
# 3. Update decisions.md (если приняли ADR)
# 4. Commit
git add .cursor/memory_bank/
git commit -m "docs: update memory bank after [component] session"
```

---

## 📋 Roadmap (16 недель до MVP)

### Milestone 1: "Скелет + Истина" (Week 1-4) ✅ COMPLETE
**Goal:** Доказать Zero Hallucination для простых запросов

- [x] Week 1: Scaffolding + Infrastructure (TimescaleDB, ChromaDB, Docker)
- [x] Week 2: VEE Sandbox + YFinance Adapter + Truth Boundary Gate
- [x] Week 3: LangGraph State Machine + Neo4j + FETCH Node
- [x] Week 4: Doubter Agent + Temporal Integrity Module + Real API

**Acceptance:** ✅ 206 tests passing, Hallucination Rate = 0%

### Milestone 2: "Advanced Optimization + Frontend" (Week 5-8) ✅ COMPLETE
**Goal:** DSPy Optimization + Production-Ready MVP

- [x] Week 5: DSPy Optimization + Debate System + DeepSeek R1
- [x] Week 6: Expanded Training (23 examples) + REST API Endpoints
- [x] Week 7: Production Deployment (Docker, CI/CD, Kubernetes)
- [x] Week 8: Next.js Frontend MVP (Query Builder, Real-Time, Results Dashboard, Charts)

**Acceptance:** ✅ 290 tests, MVP Frontend Complete, Production Infrastructure Ready

### Milestone 3: "Production Readiness" (Week 9-12) ⏳ IN PROGRESS (20%)
**Goal:** Quality Assurance + Zero Hallucination Guarantee

- [x] **Week 9 Day 1-2:** Golden Set Validation Framework + Orchestrator Integration **← СЕЙЧАС ТУТ**
- [ ] Week 9 Day 3: Domain Constraints Validation
- [ ] Week 9 Day 4: Confidence Calibration (ECE < 0.05)
- [ ] Week 9 Day 5: Load Testing + WebSocket Backend
- [ ] Week 10: Advanced Analytics + Real-Time Monitoring
- [ ] Week 11: Sensitivity Harness + Stability Analysis
- [ ] Week 12: Performance Optimization + Documentation

**Acceptance:** Accuracy ≥90%, Hallucination Rate = 0%, Load Test 100 users

### Milestone 4: "Production Launch" (Week 13-16) 📋 PLANNED
**Goal:** Shadow Mode → Production Deployment

- [ ] Week 13: Security Audit (Opus) + Penetration Testing
- [ ] Week 14: Cost Tracking + Resource Optimization
- [ ] Week 15: 100-Query Task Suite + Validation
- [ ] Week 16: Production Launch + Monitoring Setup

**Acceptance:** All metrics GREEN, Ready for Production

---

## 🔒 Security Constraints

### VEE Sandbox
- **Network:** Whitelist ONLY (api.stlouisfed.org, query.yahooapis.com)
- **Filesystem:** Read-only workspace, NO host access
- **Resources:** 2GB RAM, 60 sec timeout, 2 CPU cores
- **Pre-execution:** Static analysis (no eval, no os.system, no subprocess)

### Secrets
- **NO hardcoded secrets**: Environment variables ONLY
- **NO secrets in logs**: Redact before logging
- **NO secrets in Git**: .env.example template, .env in .gitignore

### CoT Storage (CRITICAL)
**ЗАПРЕЩЕНО хранить raw Chain-of-Thought.**
- ❌ `raw_cot: string`
- ❌ `thinking_steps: List[str]`
- ✅ `decision_operators: List[str]` (structured only)
- ✅ `reasoning_summary: str` (2-3 sentences MAX)

---

## ✅ Testing Strategy

### TDD Workflow (MANDATORY)
**Red → Green → Refactor → Update Memory**

1. **Day 1-2:** Write FAILING tests (Red)
2. **Day 3-4:** Implement до прохождения (Green)
3. **Day 5:** Refactor + Opus review → новые тесты

### Coverage Requirements
- **Truth Boundary Gate:** 95% (zero hallucination блокирующая)
- **Temporal Integrity:** 95% (look-ahead bias блокирующая)
- **VEE Sandbox:** 90%
- **Everything else:** 80%

### Test Organization
```
tests/
├── unit/          # Fast (<10 sec total)
├── integration/   # Multi-component (minutes)
├── e2e/           # Full pipeline (10+ min)
└── regression/    # Known bugs (永久)
```

---

## 🎨 Code Style

### Python
- **Formatter:** Black (line length 100)
- **Linter:** Ruff
- **Type checker:** mypy (strict mode)
- **Docstrings:** Google style
- **Type hints:** Обязательны для всех функций

### Git Commits
```bash
# Conventional Commits
feat(vee): add Docker network isolation
fix(truth-gate): handle percentages correctly
test(temporal): add publication lag edge cases
docs: update memory bank after VEE session
```

---

## 🧠 Model Strategy (Opus $50 Промо)

### Default: Sonnet (экономия)
- Code implementation
- Refactoring
- Unit tests
- Documentation

### Escalate to Opus:
- Architectural decisions (Week 0, 7, 9, 14)
- Security audits (Week 2, 15)
- Complex debugging
- Research новых технологий

**Budget Allocation:**
- Week 0 (setup): $8-11
- Week 1-4 (M1): $2-4
- Week 5-8 (M2): $5-7
- Week 9-12 (M3): $5-7
- Week 13-16 (M4): $6-8
- Reserve: $5-10

---

## 📖 Documentation Locations

| Документ | Назначение | Частота обновления |
|----------|------------|-------------------|
| **CLAUDE.md** (этот файл) | Root Anchor, команды, архитектура | Редко (при major changes) |
| **projectbrief.md** | Elevator pitch, бизнес-цели | Редко |
| **activeContext.md** | Текущий фокус, блокеры, next step | Каждая сессия |
| **decisions.md** | ADR журнал | При архитектурных решениях |
| **progress.md** | Трекер задач, метрики | После завершения задач |
| **systemPatterns.md** | Архитектурные паттерны | При появлении новых паттернов |

---

## ⚠️ Критические Правила

1. **NO плейсхолдеров**: Никаких `...`, `rest of implementation`, `TODO` без issue
2. **TDD всегда**: Тест СНАЧАЛА, код ПОТОМ
3. **Memory Bank discipline**: Update после КАЖДОЙ сессии
4. **NO raw CoT storage**: Только structured decisions
5. **Fail-closed**: Неопределенность → UNCERTAIN, не выдумывать
6. **Security first**: VEE isolation, secrets management, input validation

---

## 🆘 When Stuck

1. **Check Memory Bank:**
   ```bash
   # Прочитай последний контекст
   Read .cursor/memory_bank/activeContext.md
   Read .cursor/memory_bank/decisions.md
   ```

2. **Check open ADRs:**
   - ADR-005: ClickHouse vs TimescaleDB (блокирует Week 1)
   - ADR-006: Qdrant vs ChromaDB (блокирует Week 2)

3. **Escalate to Opus:**
   ```bash
   /model opus
   "Изучи [context], спроектируй [component]"
   ```

4. **Ask user:**
   - Если architecture decision нужен input
   - Если requirements unclear

---

## 📞 Quick Reference

### Files to Read at Session Start
```
ВСЕГДА:
- .cursor/memory_bank/activeContext.md  (что было вчера, next step)

ПО НЕОБХОДИМОСТИ:
- .cursor/memory_bank/projectbrief.md  (если забыл цели)
- .cursor/memory_bank/decisions.md     (если нужны ADR)
- .cursor/memory_bank/systemPatterns.md (если нужны паттерны)
```

### Pre-Commit Checklist
- [ ] Tests passed (`pytest tests/`)
- [ ] Coverage ≥80% (`pytest --cov`)
- [ ] Linters passed (`black`, `ruff`, `mypy`)
- [ ] No плейсхолдеров (`grep -r "\.\.\."`
- [ ] activeContext.md updated
- [ ] progress.md updated (if task done)

---

## 🎯 Current Status

**Phase:** Week 9 Day 3 - Golden Set Validation & Critical Fixes
**Progress:** [█████████░] 95%
**Blockers:** NONE

**Recent Achievements:**
- ✅ Week 8 Complete: MVP Frontend with Next.js + shadcn/ui (6,330 LOC)
- ✅ Week 9 Day 1: Golden Set Validation Framework (30 queries, 16 tests, 100% passing)
- ✅ Week 9 Day 2: Orchestrator Integration (6 integration tests, all passing)
- ✅ Week 9 Day 2-3: **Prediction Dashboard** (TimescaleDB, 7 API endpoints, 3 frontend components, 69 tests)
- ✅ Week 9 Day 3: **Critical Fixes** (source_verified field, retry mechanism, Sharpe/Volatility examples)
- ✅ Week 9 Day 3: **Merge to master** (claude/week11-router-cicd, +18,820 insertions)

**Current Status:**
- **Tests:** 621 total (585+ passing, 94.2%)
- **Code:** ~20,013 LOC backend + 6,330 LOC frontend = 26,343 LOC total
- **Components:** 17 backend modules + 36 frontend components
- **Coverage:** 99.8% (tested modules)
- **Golden Set:** 🔄 Run #2 in progress (task baab004, ~15 min remaining)

**Golden Set Validation Progress:**
- **Run #1:** 73.33% (22/30) - baseline after Fix #1-3
  - Beta: 5/5 (100%) ✅
  - Correlation: 10/10 (100%) ✅
  - Volatility: 4/5 (80%)
  - Sharpe ratio: 3/10 (30%) ❌
- **Fix #4-5 Applied:** Simplified Sharpe + Added Volatility examples
- **Run #2:** In progress (expected 90-100%)

**Next Actions:**
→ Await Golden Set Run #2 completion (~15 minutes)
→ Analyze results and update baseline report
→ If ≥90%: Production baseline achieved! 🎯
→ If <90%: Debug failures and iterate

**Ready for:** Production baseline validation (≥90% accuracy target)

---

*Этот файл — единственный источник правды о проекте APE 2026*
*При рассинхронизации с другими документами — CLAUDE.md побеждает*
*Last Updated: 2026-02-09*
*Version: 0.9.3 (Week 9 Day 3 - Golden Set Validation)*
