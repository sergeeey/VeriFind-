# 🚀 APE 2026 - START HERE (Для нового LLM)

**Проект:** Autonomous Prediction Engine 2026
**Статус:** Week 8 Day 4 Complete ✅
**Следующий шаг:** Week 8 Day 5 - Financial Visualizations + Production Polish

---

## ⚡ Quick Start (3 шага)

### 1️⃣ Прочитай эти файлы (ОБЯЗАТЕЛЬНО!)

**В ТАКОМ ПОРЯДКЕ:**

```
1. CLAUDE.md                                    # Root Anchor - архитектура проекта
2. .cursor/memory_bank/activeContext.md         # Текущий статус, последняя сессия
3. .cursor/memory_bank/progress.md              # Детальный прогресс
4. CONTINUATION_PLAN.md                         # ← Детальный план продолжения (ГДЕ ВСЕГДА ВСЕ!)
5. docs/weekly_summaries/week_08_plan.md        # План Week 8 Days 2-5
```

**5 минут чтения = понимание всего проекта!**

---

### 2️⃣ Установи Frontend Dependencies

```bash
cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\frontend"
npm install
npm run dev
```

**Ожидаемый результат:**
- Dev server на `http://localhost:3000`
- Landing page с темой (dark/light toggle)
- Login работает с demo key: `sk-ape-demo-12345678901234567890`

---

### 3️⃣ Начни Week 8 Day 5

**Открой:** `CONTINUATION_PLAN.md` или `activeContext.md` для деталей

**Создай 8 файлов по чек-листу:**
- [ ] CandlestickChart (TradingView)
- [ ] ConfidenceTrendChart (Recharts)
- [ ] DebateDistributionChart (Pie chart)
- [ ] ExecutionTimeHistogram (Bar chart)
- [ ] FactTimelineChart (Area chart)
- [ ] ChartContainer (Wrapper)
- [ ] TimeRangeSelector (Range buttons)
- [ ] types/charts.ts (TypeScript types)
- [ ] TypeScript types

**Следуй чек-листу → Тестируй → Создай summary**

---

## 📂 Структура Проекта (Краткая)

```
E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\
├── CLAUDE.md                          # 🔴 ЧИТАТЬ ПЕРВЫМ
├── CONTINUATION_PLAN.md               # 🔴 Детальный план
├── .cursor/memory_bank/               # 🔴 Memory Bank (обязательно!)
│   ├── activeContext.md              # Текущий статус
│   ├── progress.md                   # Прогресс
│   ├── projectbrief.md               # Бизнес-цели
│   └── decisions.md                  # Архитектурные решения
├── src/                              # Backend (Python, FastAPI)
├── frontend/                         # ← Frontend (Next.js 14) NEW!
│   ├── app/                          # Pages
│   ├── components/                   # React components
│   ├── lib/                          # API, store, utils
│   └── README.md                     # Frontend setup guide
├── docs/weekly_summaries/            # Summaries по дням
├── helm/ape-2026/                    # Kubernetes Helm charts
└── docker-compose.yml                # Infrastructure
```

---

## ✅ Что УЖЕ СДЕЛАНО

### Backend (95% Complete)
- ✅ VEE Sandbox (Docker code execution)
- ✅ Truth Boundary Gate (0% hallucination)
- ✅ FastAPI REST API (5 endpoints)
- ✅ LangGraph State Machine
- ✅ 290 tests (278+ passing)

### Deployment (100% Complete)
- ✅ Docker + docker-compose
- ✅ GitHub Actions CI/CD
- ✅ Kubernetes Helm charts
- ✅ Blue-green deployment

### Frontend (80% Complete) ← LAST WORK
- ✅ **Day 2 Complete:** Next.js 14 setup (35 files, 3,200 LOC)
  - Pages: Landing, Login, Register, Dashboard
  - Components: Navbar, Sidebar, 11 shadcn/ui
  - API client, Zustand store, Utils
- ✅ **Day 3 Complete:** Query Builder + WebSocket (8 files, 810 LOC)
  - QueryBuilder, QueryStatus, WebSocketProvider
  - Real-time updates, polling fallback
- ✅ **Day 4 Complete:** Results Dashboard (11 files, 1,620 LOC)
  - FactsTable (sortable, paginated)
  - DebateViewer, SynthesisCard, CodeViewer
  - Export JSON/CSV, Tabs navigation
- 📋 **Day 5 Next:** Visualizations (8 files, 1,000 LOC)

---

## 🎯 Next Task: Week 8 Day 5

**Цель:** Financial Visualizations + Production Polish

**Deliverables:**
1. TradingView Lightweight Charts (candlestick charts)
2. Recharts analytics (confidence trends, metrics)
3. Time range selector (1D, 1W, 1M, 3M, 1Y, ALL)
4. Verified fact markers on timeline
5. Framer Motion animations
6. Performance optimization (Lighthouse >90)
7. Production build

**Время:** 8-10 часов

**Детали:** См. `activeContext.md` секция "Week 8 Day 5"

---

## 🔧 Технический Context

### Backend API
- **URL:** `http://localhost:8000`
- **Endpoints:**
  - POST /query (submit query)
  - GET /status/{query_id} (get status)
  - GET /health (health check)

### Frontend
- **Framework:** Next.js 14 (App Router)
- **UI:** shadcn/ui + Tailwind CSS
- **State:** Zustand
- **Auth:** API key (demo: `sk-ape-demo-12345678901234567890`)

### WebSocket
- **Endpoint:** `ws://localhost:8000/ws`
- **⚠️ Status:** NOT YET IMPLEMENTED (use polling fallback)

---

## 📊 Progress Metrics

| Metric | Value |
|--------|-------|
| **Overall Progress** | 88% (Week 8 Day 4 complete) |
| **Backend** | 95% complete |
| **Frontend** | 80% complete (Day 4/5) |
| **Tests** | 290 backend tests (95.5% passing) |
| **Code** | ~22,630 LOC (17K backend + 5.6K frontend) |

---

## 🆘 Если что-то не работает

### "npm install fails"
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### "Backend connection fails"
- Проверь backend running: `curl http://localhost:8000/health`
- Проверь .env.local: `NEXT_PUBLIC_API_URL=http://localhost:8000`

### "Component not found"
- Проверь npm install выполнен
- Проверь path aliases в tsconfig.json

### "Memory Bank outdated?"
- Последнее обновление: 2026-02-08 22:00 UTC
- Если работа была после этой даты - обновись из Git

---

## 📚 Ключевые Документы

| Документ | Назначение | Когда читать |
|----------|------------|--------------|
| `CLAUDE.md` | Архитектура, команды, стек | Всегда первым |
| `activeContext.md` | Текущий статус, блокеры | Перед началом работы |
| `progress.md` | Детальный прогресс | Для понимания истории |
| `CONTINUATION_PLAN.md` | План продолжения | Перед Week 8 Day 3+ |
| `week_08_plan.md` | Week 8 детали | Для Days 2-5 |

---

## ✨ Философия Проекта

**КОНТЕКСТ > КОД**

1. **Security First** - Безопасность превыше всего
2. **Fresh Context** - Чистый контекст лучше мусора
3. **Verify Before Trust** - Никогда не доверять без тестов
4. **Memory Persistence** - Документировать все решения
5. **Human as Orchestrator** - Человек стратег, AI исполнитель

---

## 🎯 Success Criteria для Week 8 Day 5

- [ ] TradingView candlestick charts работают
- [ ] Recharts analytics отображаются
- [ ] Time range selector функционирует
- [ ] Verified fact markers на timeline
- [ ] Framer Motion animations smooth
- [ ] Mobile responsive
- [ ] Production build успешен
- [ ] Lighthouse score >90
- [ ] Summary создан (`week_08_day_05_summary.md`)
- [ ] Memory Bank обновлен (activeContext, progress)

---

## 🚀 Let's Go!

1. **Читай:** `CLAUDE.md` → `activeContext.md` → `progress.md`
2. **Установи:** `cd frontend && npm install`
3. **Проверь:** `npm run dev` (localhost:3000 должен открыться)
4. **Начинай:** Week 8 Day 5 по плану из `activeContext.md`

**Удачи!** 🎉

---

*Этот файл - точка входа для нового LLM*
*Обновлен: 2026-02-09 01:30 UTC*
*Статус: Week 8 Day 4 Complete, Ready for Day 5 (Final Sprint!)*
