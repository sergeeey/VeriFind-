# 🚀 START HERE - APE 2026

**Полный запуск за 10 минут** | Обновлено: 2026-02-10

---

## ⚡ Express Setup (Самое быстрое)

```bash
# 1. Перейти в проект
cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА"

# 2. Запустить Docker сервисы (должны быть уже запущены)
docker-compose ps  # Проверка

# 3. Запустить API
python -m uvicorn src.api.main:app --reload --port 8000

# 4. Запустить Frontend (в новом терминале)
cd frontend
npm run dev

# 5. Открыть браузер
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

**Готово!** 🎉

---

## 📋 Первый раз? (Полная установка)

### 1. Установить зависимости

```bash
# Python backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. Настроить .env

Файл уже настроен! Проверьте:
```bash
# Убедитесь что пароли НЕ default
grep -E "NEO4J_PASSWORD|POSTGRES_PASSWORD|SECRET_KEY" .env
```

Если видите `CHANGE_ME` - значит нужно сгенерировать новые:
```bash
# Уже сделано! Но если нужно:
# openssl rand -hex 32  # Для паролей
# openssl rand -hex 64  # Для SECRET_KEY
```

### 3. Запустить Docker

```bash
docker-compose up -d neo4j timescaledb redis

# Дождаться healthy status (~30 секунд)
docker-compose ps
```

### 4. Запустить приложение

```bash
# Backend (терминал 1)
uvicorn src.api.main:app --reload

# Frontend (терминал 2)
cd frontend
npm run dev
```

---

## 🧪 Проверка работоспособности

```bash
# 1. Health check
curl http://localhost:8000/health
# Ожидается: {"status": "healthy", ...}

# 2. Тестовый запрос
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Calculate Sharpe ratio for AAPL from 2023-01-01 to 2023-12-31"}'

# 3. Запустить тесты
pytest tests/integration/test_api_critical.py -v
# Ожидается: 19/19 passing
```

---

## 🌐 Интерфейсы

| Что | URL | Описание |
|-----|-----|----------|
| **Frontend UI** | http://localhost:3000 | Главный интерфейс (Next.js) |
| **API Docs** | http://localhost:8000/docs | Swagger UI для API |
| **Health** | http://localhost:8000/health | Проверка системы |
| **Neo4j Browser** | http://localhost:7474 | Граф знаний (neo4j / пароль из .env) |

---

## 📚 Дальше что?

### Для пользователей
1. 📖 Прочитайте **GETTING_STARTED.md** (полное руководство)
2. 🌐 Откройте **Frontend** и попробуйте Query Builder
3. 📊 Смотрите прогнозы на `/dashboard/predictions`

### Для разработчиков
1. 🧪 Изучите **tests/** (примеры использования)
2. 📂 Смотрите **.cursor/memory_bank/** (архитектура)
3. 🚀 Читайте **docs/deployment/** (production deploy)

---

## ⚠️ Важно!

- ✅ **Docker сервисы должны быть запущены** (Neo4j, Redis, TimescaleDB)
- ✅ **API ключи настроены** в `.env` (DeepSeek, Anthropic, OpenAI)
- ⚠️ **Это НЕ финансовый совет!** Только для образования

---

## 🆘 Проблемы?

```bash
# Docker сервисы не запускаются
docker-compose restart

# API не отвечает
# Проверьте что venv активирован
venv\Scripts\activate

# Frontend ошибка
cd frontend
rm -rf node_modules .next
npm install
npm run dev

# Тесты падают
# Убедитесь что Docker сервисы запущены и healthy
docker-compose ps
```

---

**Готово! Система запущена.** 🎉

**Следующий шаг:** Откройте http://localhost:3000 и создайте первый запрос!

**Полная документация:** `GETTING_STARTED.md`
