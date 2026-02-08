# APE 2026 - Continuation Plan for LLM
**Version:** 1.0
**Date:** 2026-02-08
**Current Status:** Week 8 Day 2 Complete
**Next:** Week 8 Day 3 - Query Builder + WebSocket

---

## 🎯 Project Overview

**APE 2026** = Autonomous Prediction Engine для финансовой аналитики с **0.00% hallucination** гарантией.

**Ключевая особенность:** LLM генерирует **код**, а не числа. Все выводы проверяются математически через VEE Sandbox.

---

## 📂 Структура Проекта

```
E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\
├── CLAUDE.md                          # Root Anchor - ПЕРВЫЙ файл для чтения
├── CONTINUATION_PLAN.md               # ← Этот файл (план продолжения)
├── .cursor/memory_bank/               # Memory Bank (обязательно читать!)
│   ├── activeContext.md              # Текущий статус, последняя сессия
│   ├── progress.md                   # Детальный прогресс по неделям
│   ├── projectbrief.md               # Бизнес-цели, метрики
│   ├── decisions.md                  # Архитектурные решения (ADR)
│   └── systemPatterns.md             # Паттерны разработки
├── docs/
│   ├── weekly_summaries/             # Summaries по дням
│   │   ├── week_08_day_01_summary.md # Helm charts
│   │   ├── week_08_day_02_summary.md # Frontend setup
│   │   └── week_08_plan.md           # Детальный план Week 8
│   └── deployment/
├── src/                              # Backend Python code
│   ├── api/main.py                   # FastAPI (5 endpoints)
│   ├── orchestration/                # LangGraph state machine
│   ├── vee/                          # Docker sandbox
│   └── ...
├── frontend/                         # ← NEW! Next.js 14 frontend
│   ├── app/                          # Next.js App Router pages
│   ├── components/                   # React components
│   ├── lib/                          # API client, store, utils
│   ├── package.json                  # Dependencies (24 packages)
│   └── README.md                     # Frontend setup guide
├── helm/ape-2026/                    # Kubernetes Helm charts
├── docker-compose.yml                # Infrastructure services
└── tests/                            # Backend tests (290 total)
```

---

## ✅ Что УЖЕ СДЕЛАНО (Week 1-8 Day 2)

### Backend (Weeks 1-6)
- ✅ **VEE Sandbox** - Docker-based code execution (256MB RAM, 30s timeout)
- ✅ **Truth Boundary Gate** - Validates all numerical outputs
- ✅ **Temporal Integrity Module** - Detects look-ahead bias (100% accuracy)
- ✅ **LangGraph State Machine** - PLAN → FETCH → VEE → GATE → DEBATE
- ✅ **Databases** - TimescaleDB, Neo4j, ChromaDB, Redis (all working)
- ✅ **FastAPI REST API** - 5 endpoints (POST /query, GET /status, etc.)
- ✅ **Tests** - 290 tests, 278+ passing (95.5%+)
- ✅ **DSPy Optimization** - PLAN node optimized with DeepSeek R1

### Deployment (Week 7)
- ✅ **Docker** - Multi-stage Dockerfile, docker-compose
- ✅ **CI/CD** - GitHub Actions (lint, test, security, deploy)
- ✅ **Blue-Green Deployment** - Zero-downtime updates

### Kubernetes (Week 8 Day 1)
- ✅ **Helm Charts** - Complete chart with 14 templates
- ✅ **Auto-scaling** - HPA (2-20 replicas)
- ✅ **Monitoring** - Prometheus + Grafana integration

### Frontend (Week 8 Day 2) ← LAST COMPLETED
- ✅ **Next.js 14** - App Router, TypeScript, Tailwind
- ✅ **shadcn/ui** - 11 components (Button, Card, Input, etc.)
- ✅ **Authentication** - API key login with health check validation
- ✅ **Pages** - Landing, Login, Register, Dashboard home
- ✅ **Layout** - Navbar + Sidebar (responsive, theme toggle)
- ✅ **API Client** - Axios with interceptors (auth, error handling)
- ✅ **State** - Zustand store (user, query, cache, UI)
- ✅ **35 files created** - ~3,200 LOC frontend

**Frontend Location:** `E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\frontend\`

---

## 📋 ЧТО НУЖНО СДЕЛАТЬ ДАЛЬШЕ

### ⚠️ КРИТИЧНО: Установка Frontend Dependencies

**Перед началом работы с frontend:**
```bash
cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\frontend"
npm install
```

**Ожидаемый результат:**
- Установка займет ~2-3 минуты
- Установятся 24+ packages (Next.js, React, Tailwind, shadcn/ui, etc.)
- Создастся `node_modules/` директория
- Появится `package-lock.json`

**Проверка работы:**
```bash
npm run dev
```
- Должен запуститься dev server на `http://localhost:3000`
- Landing page должна открыться с темой (dark по умолчанию)
- Можно протестировать логин с demo ключом: `sk-ape-demo-12345678901234567890`

---

## 🎯 Week 8 Day 3: Query Builder + WebSocket (СЛЕДУЮЩИЙ ШАГ)

### Цель
Создать интерфейс для отправки queries с **real-time отслеживанием** выполнения через WebSocket.

### Deliverables (8 файлов, ~800 LOC)

#### 1. Query Builder Page
**Файл:** `frontend/app/dashboard/query/new/page.tsx`
**Размер:** ~50 LOC

```typescript
'use client'

import { QueryBuilder } from '@/components/query/QueryBuilder'
import { Card } from '@/components/ui/card'

export default function NewQueryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">New Analysis Query</h1>
        <p className="text-muted-foreground">
          Ask APE 2026 to analyze financial data with zero hallucination
        </p>
      </div>
      <QueryBuilder />
    </div>
  )
}
```

**Что делает:**
- Wrapper page для QueryBuilder компонента
- Заголовок и описание
- Использует существующие UI компоненты из Day 2

---

#### 2. QueryBuilder Component
**Файл:** `frontend/components/query/QueryBuilder.tsx`
**Размер:** ~180 LOC

**Функционал:**
- Textarea для ввода query (с ограничением 1000 символов)
- Dropdown с примерами queries (6 категорий из `lib/constants.ts`)
- Button "Submit Query" (disabled пока query пустой)
- Button "Clear" для сброса
- Tips секция (советы по формулировке queries)
- Toast notifications для success/error

**Ключевые функции:**
- `handleSubmit()` - POST to `/api/query`, получает `query_id`, redirect на `/dashboard/query/[id]`
- `loadExample()` - Загружает пример query в textarea
- `validateQuery()` - Проверка длины, запрещенные символы

**Зависимости из Day 2:**
- `Button`, `Textarea`, `Card`, `Select` (shadcn/ui)
- `api.submitQuery()` (lib/api.ts)
- `useToast()` (lib/use-toast.ts)

**Пример кода (часть):**
```typescript
const handleSubmit = async () => {
  if (!query.trim()) {
    toast({ title: 'Error', description: 'Please enter a query', variant: 'destructive' })
    return
  }

  setLoading(true)
  try {
    const response = await api.submitQuery(query)
    const { query_id } = response.data
    toast({ title: 'Query Submitted', description: 'Redirecting to results...' })
    router.push(`/dashboard/query/${query_id}`)
  } catch (error) {
    toast({ title: 'Submission Failed', variant: 'destructive' })
  } finally {
    setLoading(false)
  }
}
```

---

#### 3. WebSocket Provider
**Файл:** `frontend/components/providers/WebSocketProvider.tsx`
**Размер:** ~120 LOC

**Функционал:**
- Устанавливает WebSocket соединение к `ws://localhost:8000/ws`
- Context API для глобального доступа
- Subscribe/unsubscribe механизм для query updates
- Auto-reconnect при disconnect (5 секунд)
- Listeners map для multiple queries

**Ключевые функции:**
- `useWebSocket()` hook - доступ к WebSocket context
- `subscribe(queryId, callback)` - подписка на updates конкретного query
- Auto-reconnect логика

**Интеграция:**
- Добавить `<WebSocketProvider>` в `app/layout.tsx` после ThemeProvider

**Пример использования:**
```typescript
const { subscribe, connected } = useWebSocket()

useEffect(() => {
  const unsubscribe = subscribe(queryId, (data) => {
    setStatus((prev) => ({ ...prev, ...data }))
  })
  return unsubscribe
}, [queryId])
```

---

#### 4. QueryStatus Component
**Файл:** `frontend/components/query/QueryStatus.tsx`
**Размер:** ~150 LOC

**Функционал:**
- Отображает текущий статус query (pending, planning, fetching, executing, etc.)
- Visual pipeline: PLAN → FETCH → VEE → GATE (с иконками и анимациями)
- Progress bar (0-100%)
- Error messages (если query failed)
- Metadata (query_id, start time)

**UI Elements:**
- Badge для state (цветной)
- Progress bar (Radix Progress component)
- Pipeline steps (5 шагов):
  - ✓ Completed (green check)
  - ⏳ Active (spinning loader)
  - ○ Pending (gray circle)
  - ✗ Failed (red X)

**Props:**
```typescript
interface QueryStatusProps {
  status: {
    query_id: string
    state: 'pending' | 'planning' | 'fetching' | 'executing' | 'validating' | 'completed' | 'failed'
    query_text: string
    current_node?: string
    progress: number
    error?: string
    created_at: string
  }
  queryId: string
}
```

---

#### 5. Query Status Page
**Файл:** `frontend/app/dashboard/query/[id]/page.tsx`
**Размер:** ~100 LOC

**Функционал:**
- Dynamic route page (`[id]` = query_id)
- Fetches initial status via `api.getStatus(queryId)`
- Subscribes to WebSocket updates
- Displays QueryStatus component
- Shows "Results Ready" card when state = 'completed'
- Link to results page (`/dashboard/results/{episode_id}`)

**Layout:**
- 2-column grid (desktop): QueryStatus (main) + QueryHistory (sidebar)
- 1-column (mobile): QueryStatus only

---

#### 6. QueryHistory Component
**Файл:** `frontend/components/query/QueryHistory.tsx`
**Размер:** ~80 LOC

**Функционал:**
- Sidebar component showing recent queries
- Fetch from `api.getRecentQueries()` (или mock данные на первом этапе)
- List с query text, timestamp, status badge
- Clickable → redirects to `/dashboard/query/[id]`

**Mock данные на первом этапе:**
```typescript
const mockHistory = [
  { id: '1', text: '50-day MA for AAPL', time: '2 hours ago', status: 'completed' },
  { id: '2', text: 'SPY vs QQQ correlation', time: '5 hours ago', status: 'completed' },
  { id: '3', text: 'TSLA volatility', time: '1 day ago', status: 'failed' },
]
```

---

#### 7. Select Component (shadcn/ui)
**Файл:** `frontend/components/ui/select.tsx`
**Размер:** ~80 LOC

**Что это:**
- shadcn/ui компонент для dropdown (examples selector)
- Использует Radix UI `@radix-ui/react-select`

**Копировать из shadcn/ui docs:**
https://ui.shadcn.com/docs/components/select

---

#### 8. TypeScript Types
**Файл:** `frontend/types/query.ts`
**Размер:** ~50 LOC

**Определяет types:**
```typescript
export type QueryState = 'pending' | 'planning' | 'fetching' | 'executing' | 'validating' | 'completed' | 'failed'

export interface QueryStatus {
  query_id: string
  state: QueryState
  query_text: string
  current_node?: string
  progress: number
  error?: string
  episode_id?: string
  created_at: string
  updated_at: string
}

export interface QuerySubmitResponse {
  query_id: string
  status: string
  message: string
}

// ... другие types
```

---

## ✅ Checklist для Week 8 Day 3

### Pre-work
- [ ] Прочитать `CLAUDE.md` (Root Anchor)
- [ ] Прочитать `.cursor/memory_bank/activeContext.md` (текущий статус)
- [ ] Прочитать `docs/weekly_summaries/week_08_plan.md` (детальный план)
- [ ] Прочитать `frontend/README.md` (frontend setup)
- [ ] Установить dependencies: `cd frontend && npm install`
- [ ] Проверить dev server: `npm run dev` (должен открыться localhost:3000)

### Implementation
- [ ] Создать `app/dashboard/query/new/page.tsx` (Query Builder Page)
- [ ] Создать `components/query/QueryBuilder.tsx` (Main form component)
- [ ] Создать `components/providers/WebSocketProvider.tsx` (WebSocket context)
- [ ] Добавить WebSocketProvider в `app/layout.tsx`
- [ ] Создать `components/query/QueryStatus.tsx` (Status display)
- [ ] Создать `app/dashboard/query/[id]/page.tsx` (Status page)
- [ ] Создать `components/query/QueryHistory.tsx` (Recent queries)
- [ ] Создать `components/ui/select.tsx` (shadcn Select component)
- [ ] Создать `types/query.ts` (TypeScript types)

### Testing
- [ ] Test query submission (должен redirect на status page)
- [ ] Test WebSocket connection (check browser DevTools Console)
- [ ] Test real-time updates (если backend WebSocket работает)
- [ ] Test progress bar (должен обновляться)
- [ ] Test error handling (submit invalid query)
- [ ] Test mobile responsiveness (sidebar collapse)

### Documentation
- [ ] Создать `docs/weekly_summaries/week_08_day_03_summary.md`
- [ ] Обновить `activeContext.md` (mark Day 3 complete)
- [ ] Обновить `progress.md` (mark Day 3 complete)

---

## 🔧 Технические Детали

### API Endpoints (Backend)
**Уже реализованы в `src/api/main.py`:**

1. **POST /query**
   - Body: `{ "query": string, "priority"?: string }`
   - Response: `{ "query_id": string, "status": string, "message": string }`

2. **GET /status/{query_id}**
   - Response: `QueryStatus` object (см. types выше)

3. **GET /health**
   - Response: `{ "status": "healthy" }`

### WebSocket Protocol
**Endpoint:** `ws://localhost:8000/ws`

**⚠️ ВАЖНО:** WebSocket НЕ ЕЩЕ реализован в backend!
На Week 8 Day 3 нужно:
- Либо реализовать WebSocket в backend (`src/api/main.py`)
- Либо использовать polling fallback (GET /status каждые 2 секунды)

**Для fallback polling:**
```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    const response = await api.getStatus(queryId)
    setStatus(response.data)
  }, 2000)
  return () => clearInterval(interval)
}, [queryId])
```

### Environment Variables
**Frontend `.env.local`:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=APE 2026
```

---

## 📊 Success Criteria для Day 3

| Критерий | Описание | Как проверить |
|----------|----------|---------------|
| Query submission | Query отправляется и возвращает query_id | Submit форму, check redirect |
| WebSocket connection | WebSocket устанавливает соединение | Check DevTools Console: "WebSocket connected" |
| Real-time updates | Status обновляется без refresh | Submit query, watch status change |
| Progress bar | Progress bar отражает текущий stage | Должен расти от 0% до 100% |
| Error handling | Error messages отображаются в toast | Submit invalid query, see toast |
| Mobile responsive | UI работает на mobile | Resize browser to 375px width |
| Example queries | Dropdown с examples загружает query | Select example, check textarea |
| Clear button | Clear button очищает textarea | Click Clear, textarea должен стать пустым |

---

## 🚀 Quick Start для Нового LLM

**Шаг 1:** Читать файлы в порядке:
1. `CLAUDE.md` (архитектура проекта)
2. `.cursor/memory_bank/activeContext.md` (текущий статус)
3. `docs/weekly_summaries/week_08_plan.md` (детальный план Week 8)
4. `CONTINUATION_PLAN.md` (этот файл)

**Шаг 2:** Установить dependencies:
```bash
cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА\frontend"
npm install
npm run dev
```

**Шаг 3:** Проверить backend:
```bash
cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА"
# Backend должен быть запущен на localhost:8000
# Проверить: curl http://localhost:8000/health
```

**Шаг 4:** Начать Week 8 Day 3:
- Создать 8 файлов по списку выше
- Следовать чек-листу
- Тестировать по ходу разработки

**Шаг 5:** По завершению:
- Создать summary (`week_08_day_03_summary.md`)
- Обновить Memory Bank (activeContext, progress)
- Commit с message: `feat(frontend): add query builder + WebSocket (Week 8 Day 3)`

---

## 📚 Полезные Ссылки

### Документация
- [Next.js 14 Docs](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand](https://zustand-demo.pmnd.rs/)
- [Axios](https://axios-http.com/docs/intro)

### Существующий код (для reference)
- `frontend/lib/api.ts` - API client pattern
- `frontend/lib/store.ts` - Zustand store pattern
- `frontend/components/layout/Navbar.tsx` - Component example
- `frontend/app/login/page.tsx` - Form handling example

---

## ⚠️ Важные Замечания

### 1. Backend API должен быть запущен
Frontend зависит от backend API на `localhost:8000`. Убедитесь, что backend running перед тестированием frontend.

### 2. WebSocket может не работать сразу
Если WebSocket endpoint не реализован в backend, используйте polling fallback (см. выше).

### 3. Demo API Key
Для тестирования используйте: `sk-ape-demo-12345678901234567890`

### 4. Memory Bank ОБЯЗАТЕЛЕН
После каждого дня работы обновляйте:
- `activeContext.md` - что сделано, next step
- `progress.md` - отметить день как complete
- Создать day summary в `docs/weekly_summaries/`

### 5. Не изобретать велосипед
- Используйте существующие компоненты из Day 2
- Копируйте shadcn/ui компоненты из официальной docs
- Следуйте паттернам из существующего кода

---

## 🎯 Цели Week 8

**Day 3 (текущий):** Query Builder + WebSocket
**Day 4:** Results Dashboard + Verified Facts Viewer
**Day 5:** Financial Visualizations + Production Polish

**Финал Week 8:**
- Полностью рабочий frontend
- Интеграция с backend API
- Real-time updates
- Professional UI/UX
- Production-ready

**Grade Target:** A+ (95%+)

---

## 📞 Если что-то не работает

### npm install fails
```bash
rm -rf node_modules package-lock.json
npm install
```

### Dev server не запускается
- Проверить Node.js версию (должен быть 18+)
- Проверить порт 3000 (должен быть свободен)
- Проверить .env.local (должен существовать)

### Backend connection fails
- Проверить backend running: `curl http://localhost:8000/health`
- Проверить CORS в backend
- Проверить `NEXT_PUBLIC_API_URL` в .env.local

### Components not found
- Убедиться что npm install выполнен
- Проверить path aliases в tsconfig.json (`@/*` должен быть настроен)

---

**Удачи!** 🚀

*Этот план создан 2026-02-08 после завершения Week 8 Day 2.*
*Следующий LLM должен продолжить с Week 8 Day 3.*
*Все необходимые файлы и контекст находятся в проекте.*
