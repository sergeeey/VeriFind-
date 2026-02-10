# APE 2026 - Полное Руководство для Начинающих

## 📌 Что это такое?

**APE (Autonomous Prediction Engine)** — это AI-платформа для финансового анализа, которая использует искусственный интеллект для прогнозирования движения цен акций.

### Простыми словами:
- Вы задаёте вопрос: *"Что будет с акциями Apple через месяц?"*
- Система собирает данные из разных источников
- AI-агенты "обсуждают" и приходят к консенсусу
- Вы получаете прогноз с указанием уверенности

---

## 🎯 Что умеет система

### 1. Анализ запросов на естественном языке
```
Вход: "Проанализируй рост NVIDIA"
↓
Система понимает:
- Тикер: NVDA
- Действие: анализ роста
- Нужны исторические данные
```

### 2. Мульти-агентные дебаты
Два AI-агента спорят:
- **Булл** (оптимист): "Акции растут потому что..."
- **Бер** (пессимист): "Но есть риски..."
- **Синтезатор**: "Общий вывод с учётом обоих мнений"

### 3. Проверка фактов
Система не доверяет слепо AI — она:
- Берёт реальные данные с Yahoo Finance
- Сверяет заявления AI с фактами
- Выставляет оценку достоверности (0-100%)

### 4. Прогнозы с коридором
Не просто "будет расти", а:
```
Тикер: AAPL
Дата прогноза: 2026-03-10
Коридор цен:
  - Пессимистично: $175
  - Базовый сценарий: $185
  - Оптимистично: $195
Уверенность: 78%
```

### 5. Отслеживание точности
Система помнит все свои прогнозы и:
- Сверяет с реальными ценами
- Считает процент попаданий
- Показывает статистику по тикерам

### 6. Граф знаний
Хранит связи между:
- Фактами → Источникам
- Запросами → Эпизодам анализа
- Прогнозами → Результатам

---

## 🏗️ Архитектура простым языком

```
┌─────────────────────────────────────────────────────────────┐
│                     ВЫ ВВОДИТЕ ЗАПРОС                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  1. МАРШРУТИЗАТОР (Router)                                  │
│     - Определяет тип запроса                                │
│     - Выбирает стратегию                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  2. ПЛАНИРОВЩИК (Planner)                                   │
│     - Создаёт план действий                                 │
│     - Какие данные нужны, какие шаги выполнить              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  3. СБОР ДАННЫХ (Fetcher)                                   │
│     - Запрашивает Yahoo Finance                             │
│     - Получает цены, объёмы, новости                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  4. ДЕБАТЫ (Debate)                                         │
│     ┌─────────────┐         ┌─────────────┐                 │
│     │  Булл Агент │ ←────→ │  Бер Агент  │                 │
│     │  (За рост)  │   Спор │ (Против)    │                 │
│     └─────────────┘         └─────────────┘                 │
│            ↓                      ↓                         │
│            └──────────┬──────────┘                          │
│                       ↓                                     │
│              Синтез мнений                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  5. ПРОВЕРКА (Truth Gate)                                   │
│     - Проверяет факты                                       │
│     - Выставляет confidence score                           │
│     - Фильтрует сомнительные утверждения                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  6. ПРОГНОЗ (Predictor)                                     │
│     - Создаёт коридор цен                                   │
│     - Сохраняет в базу                                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     ВЫ ПОЛУЧАЕТЕ ОТВЕТ                     │
│              (с дисклеймером о рисках)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Быстрый старт (5 минут)

### Шаг 1: Клонируйте репозиторий
```bash
git clone <repository-url>
cd ape-2026
```

### Шаг 2: Создайте окружение
```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 3: Настройте окружение
```bash
# Скопируйте пример
COPY .env.example .env

# Отредактируйте .env файл:
# - Добавьте API ключи (OpenAI, Anthropic, DeepSeek)
# - Установите пароли для баз данных
```

### Шаг 4: Запустите инфраструктуру
```bash
# Запуск через Docker
docker-compose up -d neo4j timescaledb redis

# Проверка
# Neo4j: http://localhost:7474
# Redis: localhost:6380
# Postgres: localhost:5433
```

### Шаг 5: Запустите API
```bash
# Через uvicorn
uvicorn src.api.main:app --reload --port 8000

# Или через Docker
docker-compose up -d api
```

### Шаг 6: Проверьте работу
```bash
# Health check
curl http://localhost:8000/health

# Должно вернуть:
{"status": "healthy", "version": "1.0.0", ...}
```

---

## 📖 Как пользоваться API

### 1. Проверка здоровья системы
```bash
# Простая проверка
curl http://localhost:8000/health

# Готовность к работе (для Kubernetes)
curl http://localhost:8000/ready

# Жив ли сервис
curl http://localhost:8000/live
```

### 2. Создание запроса на анализ
```bash
# POST запрос
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Проанализируй акции Tesla на ближайший месяц"
  }'

# Ответ:
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Query accepted for processing",
  "estimated_time_seconds": 30,
  "disclaimer": "This analysis is for informational purposes only..."
}
```

### 3. Получение результата
```bash
# Используйте query_id из предыдущего ответа
curl http://localhost:8000/api/status/550e8400-e29b-41d4-a716-446655440000
```

### 4. Быстрый анализ (синхронно)
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Calculate Sharpe ratio for AAPL"
  }'

# Ждёт завершения и возвращает результат сразу
```

### 5. Работа с прогнозами
```bash
# Получить все прогнозы
curl http://localhost:8000/api/predictions/

# Получить прогнозы по тикеру
curl http://localhost:8000/api/predictions/?ticker=AAPL

# Получить последний прогноз
curl http://localhost:8000/api/predictions/AAPL/latest

# Получить историю прогнозов
curl http://localhost:8000/api/predictions/AAPL/history

# Получить ценовой коридор
curl http://localhost:8000/api/predictions/AAPL/corridor?limit=10

# Получить статистику точности
curl http://localhost:8000/api/predictions/track-record
```

### 6. Проверка прогнозов против реальности
```bash
# Обновить прогнозы актуальными ценами
curl -X POST "http://localhost:8000/api/predictions/check-actuals?days_until_target=7"
```

---

## 💻 Примеры использования

### Пример 1: Анализ одной акции
```python
import requests

# 1. Запрос на анализ
response = requests.post(
    "http://localhost:8000/api/analyze",
    json={"query": "Проанализируй Apple"}
)
result = response.json()

# 2. Вывод результата
print(f"Ответ: {result['answer']}")
print(f"Уверенность: {result['verification_score']}%")
print(f"Источник данных: {result['data_source']}")
```

### Пример 2: Получение прогноза
```python
import requests

ticker = "TSLA"

# Получить коридор цен
response = requests.get(
    f"http://localhost:8000/api/predictions/{ticker}/corridor",
    params={"limit": 5}
)
data = response.json()

for item in data['corridor_data']:
    print(f"Дата: {item['target_date']}")
    print(f"  Диапазон: ${item['price_low']} - ${item['price_high']}")
    print(f"  Базовая: ${item['price_base']}")
    if item['actual_price']:
        print(f"  Реальная: ${item['actual_price']} {'✅' if item['is_hit'] else '❌'}")
```

### Пример 3: Отслеживание точности
```python
import requests

# Получить статистику
response = requests.get(
    "http://localhost:8000/api/predictions/track-record",
    params={"ticker": "AAPL"}
)
stats = response.json()['track_record']

print(f"Всего прогнозов: {stats['total_predictions']}")
print(f"Попаданий: {stats['hit_rate']:.1%}")
print(f"Близких: {stats['near_rate']:.1%}")
print(f"Промахов: {stats['miss_rate']:.1%}")
```

---

## 🐳 Запуск через Docker (рекомендуется)

### Полный стек
```bash
# Запуск всего
docker-compose up -d

# Состав:
# - API (порт 8000)
# - Neo4j (порт 7474, 7688)
# - TimescaleDB (порт 5433)
# - Redis (порт 6380)
# - Grafana (порт 3001)
# - Prometheus (порт 9091)
```

### Проверка логов
```bash
# API
docker-compose logs -f api

# Базы данных
docker-compose logs -f neo4j
docker-compose logs -f timescaledb
```

### Остановка
```bash
docker-compose down

# С удалением данных
docker-compose down -v
```

---

## 🧪 Тестирование

### Запуск тестов
```bash
# Критические тесты (быстро)
python -m pytest tests/integration/test_api_critical.py -v

# Все тесты (медленно)
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ --cov=src --cov-report=term
```

### Нагрузочное тестирование
```bash
# Установить Locust
pip install locust

# Запуск
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Открыть http://localhost:8089
# Установить: 50 users, spawn rate: 10
```

---

## 📊 Мониторинг

### Prometheus
```
URL: http://localhost:9091
Метрики:
- http_requests_total - количество запросов
- ape_queries_total - бизнес-метрики
- ape_accuracy - точность прогнозов
```

### Grafana
```
URL: http://localhost:3001
Логин: admin
Пароль: admin123

Дашборды:
- API Performance
- Business Metrics
- System Health
```

### Health Checks
```bash
# Проверка компонентов
curl http://localhost:8000/health | python -m json.tool

# Пример ответа:
{
  "status": "healthy",
  "components": {
    "neo4j": "up",
    "timescaledb": "up",
    "redis": "up"
  }
}
```

---

## ⚠️ Важные замечания

### 1. Дисклеймер
**ВСЕ ПРОГНОЗЫ — НЕ ФИНАНСОВЫЕ СОВЕТЫ!**
- Система для образовательных целей
- Всегда консультируйтесь с финансовым advisor
- Прошлые результаты не гарантируют будущие

### 2. API Keys
- Не коммитьте `.env` в git
- Используйте разные ключи для dev/prod
- Установите лимиты на расходы

### 3. Ограничения
- Бесплатные API имеют rate limits
- Сложные запросы могут занимать 10-30 секунд
- Не все тикеры доступны (см. `/api/data/tickers`)

### 4. Безопасность
- Смените все пароли по умолчанию
- Используйте HTTPS в production
- Ограничьте доступ к `/docs` в production

---

## 🆘 Troubleshooting

### Проблема: "Connection refused"
```bash
# Проверьте, запущены ли сервисы
docker-compose ps

# Перезапустить
docker-compose restart
```

### Проблема: "API key invalid"
```bash
# Проверьте .env файл
cat .env | grep API_KEY

# Перезагрузить окружение
# Windows: .
. .env
```

### Проблема: Тесты не проходят
```bash
# Убедитесь, что сервисы запущены
docker-compose up -d

# Запустить только критические тесты
python -m pytest tests/integration/test_api_critical.py -v
```

### Проблема: Медленные запросы
```bash
# Проверьте Circuit Breaker
curl http://localhost:8000/api/predictions/

# Если 503 - подождите 60 секунд (timeout)
# Или перезапустите API
```

---

## 📚 Полезные ссылки

Внутри проекта:
- `docs/PRODUCTION_DEPLOY.md` — Полное руководство по деплою
- `docs/security/API_KEY_MANAGEMENT.md` — Управление ключами
- `.memory_bank/` — Техническая документация
- `tests/` — Примеры использования в тестах

Внешние ресурсы:
- FastAPI Docs: https://fastapi.tiangolo.com
- Neo4j Browser: http://localhost:7474
- API Docs (Swagger): http://localhost:8000/docs

---

## 🎓 Первые шаги: Чеклист

- [ ] Клонировать репозиторий
- [ ] Создать виртуальное окружение
- [ ] Установить зависимости
- [ ] Создать `.env` с API ключами
- [ ] Запустить `docker-compose up -d`
- [ ] Проверить `/health`
- [ ] Сделать тестовый запрос
- [ ] Открыть Swagger UI (`/docs`)
- [ ] Запустить тесты
- [ ] Поздравить себя! 🎉

---

## 💬 Получить помощь

Если что-то не работает:
1. Проверьте логи: `docker-compose logs -f api`
2. Запустите health check: `curl localhost:8000/health`
3. Проверьте `.env` файл
4. Перезапустите сервисы: `docker-compose restart`

---

**Удачного использования APE 2026!** 🚀

*Помните: это инструмент для анализа, не финансовый советник.*
