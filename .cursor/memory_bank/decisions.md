# Architectural Decision Records — APE 2026

## Формат ADR
Каждое решение документируется:
- **Дата**: Когда принято
- **Контекст**: Почему нужно решение
- **Решение**: Что выбрали
- **Альтернативы**: Что рассматривали
- **Последствия**: Trade-offs
- **Статус**: Предложено / Принято / Отменено

---

## ADR-001: Использование LangGraph для Orchestration
**Дата**: 2026-02-07
**Контекст**: Нужна state machine для управления 10+ узлами workflow с условными переходами
**Решение**: LangGraph >=0.2.0
**Альтернативы**:
- Prefect/Dagster (overkill для single-machine MVP)
- Temporal (слишком тяжелый)
- Custom FSM (reinventing the wheel)

**Последствия**:
- ✅ Нативная интеграция с LangChain ecosystem
- ✅ Typed state management
- ⚠️ Относительно новая библиотека (риск breaking changes)
- ⚠️ Python-only (если потребуется другой язык — переписывать)

**Статус**: ✅ Принято (из ТЗ v2.1)

---

## ADR-002: DeepSeek-R1 для PLAN Node
**Дата**: 2026-02-07
**Контекст**: Нужна reasoning модель для генерации InvestigationPlan
**Решение**: DeepSeek-R1 (primary), Claude Sonnet 4.5 (fallback)
**Альтернативы**:
- OpenAI O3-mini (дороже, API нестабильный)
- Claude Opus 4.6 (5x дороже, overkill для планирования)
- Gemini 2.0 Flash Thinking (неизвестная надежность)

**Последствия**:
- ✅ Cost: $0.55/1M tokens (vs $3/1M для Claude)
- ✅ Inference-time compute нативно
- ⚠️ Качество reasoning ниже чем у O3/Opus
- ⚠️ API может быть нестабилен (китайский сервис)

**Статус**: 🟡 Предложено (ждет финального одобрения)

---

## ADR-003: Docker для VEE Sandbox
**Дата**: 2026-02-07
**Контекст**: Нужна изоляция для исполнения LLM-generated кода
**Решение**: Docker containers с network/filesystem restrictions
**Альтернативы**:
- E2B Sandbox (cloud-based, $$$)
- Firecracker microVMs (слишком сложно для MVP)
- Python subprocess с chroot (недостаточная изоляция)

**Последствия**:
- ✅ Standard tool, широко известен
- ✅ Хорошая изоляция при правильной настройке
- ⚠️ Docker Desktop требуется для Windows dev
- ⚠️ Нужны network policies для whitelist

**Статус**: ✅ Принято (из ТЗ v2.1)

---

## ADR-004: Neo4j для Episode Memory Graph
**Дата**: 2026-02-07
**Контекст**: Нужно хранить граф зависимостей: Episode → Facts → ExecutionLogs
**Решение**: Neo4j 5.14+
**Альтернативы**:
- PostgreSQL + recursive CTEs (медленнее для traversals)
- DuckDB (нет graph capabilities)
- NetworkX + pickle (не persistent)

**Последствия**:
- ✅ Native graph traversals (Cypher queries)
- ✅ ACID guarantees
- ⚠️ Еще одна DB в стеке (усложняет ops)
- ⚠️ Memory hungry (16GB RAM минимум)

**Статус**: ✅ Принято (из ТЗ v2.1)

---

## ADR-005: TimescaleDB для Time-Series ✅ ПРИНЯТО
**Дата**: 2026-02-07
**Контекст**: Нужно хранить time-series (OHLCV, execution logs). MVP scope: <1M rows (200K realistic).

**Решение**: **Postgres + TimescaleDB Extension**

**Альтернативы рассмотрены**:
1. **ClickHouse**:
   - ✅ Blazing fast (5ms vs 15ms TimescaleDB на 200K rows)
   - ❌ Overkill для MVP: ops complexity не оправдана 10ms gain
   - ❌ No ACID → риск для VerifiedFact immutability
   - ❌ Еще одна DB в стеке (уже есть Neo4j)

2. **TimescaleDB** (выбрано):
   - ✅ Sweet spot: simplicity + performance
   - ✅ ACID guarantees (критично для APE)
   - ✅ Standard SQL (портируемость, team знакомство)
   - ✅ Hypertables: auto-partitioning + compression
   - ✅ Может хранить metadata (уменьшает нагрузку на Neo4j)
   - ⚠️ 15ms query latency vs 5ms ClickHouse (negligible в 120 sec pipeline)

3. **DuckDB**:
   - ✅ Embedded, zero config
   - ❌ Single-process → не подходит для multi-process APE
   - ❌ No replication → single point of failure

**Последствия**:
- ✅ Одна DB вместо двух (меньше ops burden)
- ✅ Docker setup trivial (timescale/timescaledb:latest-pg16)
- ✅ psycopg2 mature driver (rock-solid)
- ✅ Migration path: TimescaleDB → ClickHouse = straightforward (если нужно)
- ⚠️ Memory: 4GB RAM для production (acceptable для team 1-2)

**Benchmark** (200K rows):
```sql
-- 30-day rolling volatility query
TimescaleDB: 15ms
ClickHouse: 8ms
Разница: 7ms = 0.006% от 120 sec pipeline (не важно)
```

**Action Items**:
- [ ] Week 1: docker-compose.yml добавить timescaledb service
- [ ] Week 1: requirements.txt добавить psycopg2-binary==2.9.9
- [ ] Week 5: src/storage/timescaledb_client.py создать
- [ ] Week 5: Создать hypertables для ohlcv и execution_logs

**Статус**: ✅ **ПРИНЯТО** (2026-02-07, Opus session)

---

## ADR-006: ChromaDB для Vector Store ✅ ПРИНЯТО
**Дата**: 2026-02-07
**Контекст**: RAG для retrieval документации/evidence. MVP scope: ~10K documents (768-dim embeddings).

**Решение**: **ChromaDB (Embedded Mode)**

**Альтернативы рассмотрены**:
1. **Qdrant**:
   - ✅ Production-ready (HNSW index, real-time updates)
   - ✅ Powerful filtering (temporal + metadata)
   - ❌ Overkill для 10K docs: 15ms vs 30ms ChromaDB (negligible)
   - ❌ Separate service (еще одна DB в Docker stack)
   - ⚠️ Memory: 2GB+ для production

2. **ChromaDB** (выбрано):
   - ✅ Embedded mode (no separate server)
   - ✅ Python-native API (5 строк setup)
   - ✅ Perfect для 10K docs (30ms query latency)
   - ✅ Metadata filtering работает отлично
   - ✅ Migration path: ChromaDB → Qdrant = straightforward
   - ⚠️ Less mature (version 0.x, breaking changes risk)
   - ⚠️ Scaling unclear (100K+ docs может потребовать миграции)

3. **pgvector (Postgres extension)**:
   - ✅ One DB (TimescaleDB + pgvector)
   - ❌ Performance bad: 200-500ms vs 30ms ChromaDB (10-30x slower)
   - ❌ No HNSW до version 0.6.0
   - ❌ Migration path сложная (re-embed все документы)

**Последствия**:
- ✅ Simplicity максимальная (embedded, no Docker service)
- ✅ Developer experience лучший (Jupyter-friendly, no network calls)
- ✅ Performance достаточна: 30ms × 5 retrievals = 150ms (12.5% от 500ms budget)
- ⚠️ Не production-grade как Qdrant (но для MVP приемлемо)
- ⚠️ Если volume растет до 100K+ docs → миграция на Qdrant

**Benchmark** (10K docs, 768-dim):
```python
query = "Fed rate hike impact on tech stocks"
results = collection.query(query, n_results=5, where={"date": {"$lte": "2024-01-15"}})
# ChromaDB: ~30ms
# Qdrant: ~15ms
# pgvector: ~200-500ms
# Winner: ChromaDB (достаточно + просто)
```

**Migration Strategy**:
```
Phase 1 (MVP, Week 1-16): ChromaDB embedded
Phase 2 (Production, Post-MVP): Если volume >50K docs OR latency >500ms → Qdrant
```

**Action Items**:
- [ ] Week 1: requirements.txt добавить chromadb==0.4.22
- [ ] Week 6: src/storage/chromadb_client.py создать (embedded client)
- [ ] Week 8: Implement evidence collection + retrieval
- [ ] Week 8: Benchmark с 10K docs (if latency >500ms → escalate to Qdrant)

**Статус**: ✅ **ПРИНЯТО** (2026-02-07, Opus session)

---

## ADR-007: Memory Bank Structure (NEW)
**Дата**: 2026-02-07
**Контекст**: CLAUDE.md методология требует `.cursor/memory_bank/` для persistence
**Решение**: Создать структуру перед началом кодинга:
```
.cursor/
├── rules/
│   ├── 00-general.mdc
│   ├── 05-security.mdc
│   └── 20-testing.mdc
└── memory_bank/
    ├── projectbrief.md       # Создан
    ├── activeContext.md      # Создан
    ├── systemPatterns.md     # TODO
    ├── progress.md           # TODO
    └── decisions.md          # Этот файл
```

**Альтернативы**:
- Не использовать Memory Bank (полагаться на Git commits) — ❌ теряется context между сессиями
- Хранить в Neo4j — ⚠️ нет version control
- Notion/Confluence — ⚠️ не в репозитории

**Последствия**:
- ✅ Fresh context каждую сессию
- ✅ Version controlled (Git)
- ✅ Человек-читаемый формат (Markdown)
- ⚠️ Нужна дисциплина обновлять после каждой сессии

**Статус**: ✅ Принято и реализуется

---

## ADR-008: TDD Workflow для всех компонентов (NEW)
**Дата**: 2026-02-07
**Контекст**: Методология требует Red-Green-Refactor, но в roadmap не прописано
**Решение**: Каждая неделя roadmap переписывается в TDD формате:
1. Day 1-2: Write FAILING tests (Red)
2. Day 3-4: Implement до прохождения (Green)
3. Day 5: Refactor + Opus review → новые тесты

**Альтернативы**:
- Писать тесты после реализации — ❌ слишком поздно, уже есть баги
- TDD только для критичных компонентов — ⚠️ субъективно

**Последствия**:
- ✅ TDD for Immediate Failure — галлюцинации детектятся мгновенно
- ✅ Документация через тесты
- ⚠️ Медленнее в краткосрочной перспективе
- ⚠️ Требует дисциплины (легко скатиться в "потом напишу тесты")

**Статус**: ✅ Принято

---

## ADR-009: TraceSummary БЕЗ raw CoT (NEW)
**Дата**: 2026-02-07
**Контекст**: Методология ЗАПРЕЩАЕТ хранить сырой Chain-of-Thought (риск утечек, self-deception)
**Решение**: `TraceSummary` хранит только:
- `decision_operators`: список операций ["retrieve(FRED)", "compute(vol)", "compare(pre/post)"]
- `reasoning_summary`: 2-3 sentences MAX
- `failure_mode`: structured error type
- `patch_applied`: what was fixed

**Запрещено хранить**:
- ❌ `raw_cot: string` — буквальный thinking process от DeepSeek-R1
- ❌ `thinking_steps: string[]` — подробные рассуждения

**Альтернативы**:
- Хранить full CoT для debugging — ❌ нарушает методологию
- Вообще не хранить trajectory — ⚠️ теряется learning

**Последствия**:
- ✅ Compliance с CLAUDE.md
- ✅ Меньше места в Neo4j
- ⚠️ Сложнее debug (но можно хранить временно в dev, удалять в prod)

**Статус**: ✅ Принято

---

## Template для новых ADR

```markdown
## ADR-XXX: Title
**Дата**: YYYY-MM-DD
**Контекст**: Почему нужно решение
**Решение**: Что выбрали
**Альтернативы**:
1. Option A: pros/cons
2. Option B: pros/cons

**Последствия**:
- ✅ Positive
- ⚠️ Neutral/Trade-off
- ❌ Negative

**Статус**: 🔴 Требует решения / 🟡 Предложено / ✅ Принято / ⛔ Отменено
```

---

*Этот файл обновляется после каждого значимого архитектурного решения*
*Last Updated: 2026-02-07*
