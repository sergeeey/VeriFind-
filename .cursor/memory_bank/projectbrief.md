# APE 2026 — Project Brief

## Elevator Pitch
Финансовая аналитическая система с гарантией zero hallucination через архитектурное разделение: LLM генерирует код, а не числа. Все выводы проверяемы математически.

## Бизнес-Цели
1. Decision-support для финансового анализа (не trading)
2. Hallucination Rate = 0.00% (блокирующая метрика)
3. Calibration Error (ECE) < 0.05
4. 100% Temporal Adherence (no look-ahead bias)
5. Готовность к Shadow Mode за 16 недель

## Ключевые Ограничения
- **No Trading**: Read-only, система не может размещать ордера
- **Fail-Closed**: При недостатке данных → UNCERTAIN, не выдумывать
- **Human-in-Loop**: Confidence < 70% → эскалация
- **Audit Trail**: Каждая операция логируется (immutable)

## Технический Стек (Решения приняты)
- Orchestration: LangGraph (Python 3.13) ✅
- Reasoning: Claude Sonnet 4.5 (Plan generation) ✅ [Week 1-2]
- Validation: Claude Sonnet 4.5 (Doubter agent) ✅ [Week 4 Day 1]
- Debate: DeepSeek-V3 (planned Week 5-6) ⏸️
- Graph DB: Neo4j 5.14+ ✅ [Week 3 Day 4]
- Time-Series: TimescaleDB (PostgreSQL 16) ✅ [ADR-005, Week 3 Day 2]
- Vector: ChromaDB (embedded mode) ✅ [ADR-006, Week 1 Day 2]
- Sandbox: Docker isolated environment ✅ [Week 2 Day 1]
- Temporal Integrity: Custom TIM (regex-based) ✅ [Week 4 Day 3]

## Команда
- 1-2 разработчика (соло возможно)
- Модель: Opus для архитектуры, Sonnet для реализации

## Success Metrics (North Star)
| Метрика | Целевое значение | Текущий статус | Реализация |
|---------|------------------|----------------|------------|
| Hallucination Rate (Numerical) | 0.00% | ✅ 0.00% (arch) | Truth Boundary Gate [Week 2 Day 3] |
| Temporal Adherence | 100% | ✅ 100% (TIM) | TemporalIntegrityChecker [Week 4 Day 3] |
| Evidence Coverage | ≥ 90% | ⏳ Not measured | Planned Week 6 |
| Test Coverage | 100% | ✅ 194/194 (100%) | TDD methodology [Week 1-4] |
| P95 Latency | < 120 sec | ✅ <5s (simple) | VEE Sandbox [Week 2 Day 1] |
| Cost per Query | < $0.10 | ⏳ Not measured | Real API pending [Week 4 Day 2] |

## Известные Риски (Updated Week 4)
1. ✅ ~~Temporal Integrity Module~~ — RESOLVED (Week 4 Day 3, TIM implemented)
2. ⚠️ Calibration требует 3+ месяцев shadow mode
3. 🟡 Cost management — infrastructure ready, pending real API validation
4. ✅ ~~Latency~~ — <5s for simple queries, <120s achievable

## Документация
- Техническое задание: `E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\ТЕХНИЧЕСКОЕ ЗАДАНИЕ_ APE 2026 v2.1 — Autonomous Pr.md`
- Методология: `E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\Методология создания проекта.txt`
- Prompt Methodology: `.cursor/memory_bank/promptMethodology.md` [NEW Week 4]
- Testing Guide: `docs/TESTING.md` [NEW Week 4 Day 2]
- System Patterns: `.cursor/memory_bank/systemPatterns.md`
- Глобальные инструкции: `~/.claude/CLAUDE.md`

## Current Status (Week 4 Day 3)
- Version: v0.4.3 (Week 4 Day 3 Complete - TIM Integrated)
- Test Coverage: 194/194 tests passing (100%)
- Components: 13 modules fully implemented
- Critical Blockers:
  * Blocker #1 (PLAN Node): Infrastructure complete, pending API validation ⏳
  * Blocker #2 (TIM): RESOLVED ✅ (3/10 → 9/10)
  * Blocker #3 (API Layer): Deferred to Week 8-9 ⏸️

## Версия History
- v0.4.3 (2026-02-08): Week 4 Day 3 - TIM implemented, 194 tests
- v0.4.2 (2026-02-08): Week 4 Day 2 - Real API test infrastructure
- v0.4.1 (2026-02-08): Week 4 Day 1 - Doubter Agent
- v0.3.x (2026-02-07): Week 3 - LangGraph + TimescaleDB + Neo4j + FETCH
- v0.2.x (2026-02-07): Week 2 - VEE Sandbox + Truth Gate + Orchestrator
- v0.1.x (2026-02-06): Week 1 - Infrastructure + ChromaDB + PLAN + Evaluation
- v0.0.0 (2026-02-05): Pre-MVP, design-only

Last Updated: 2026-02-08 (Week 4 Day 3)
