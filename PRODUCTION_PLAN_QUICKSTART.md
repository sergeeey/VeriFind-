# 🚀 Быстрый старт: Production Readiness (2 недели)

**Цель:** 6.8/10 → 8.5/10 (production ready)  
**Срок:** 2 недели + 3 дня стабилизации  
**Старт:** 2026-02-10

---

## ✅ ЧЕКЛИСТ ПЕРЕД СТАРТОМ

### Критично (обязательно):
- [ ] Отозвать ВСЕ API ключи из `.env`
- [ ] Сгенерировать новые ключи
- [ ] Убедиться что `docker-compose up -d` работает
- [ ] Проверить что `pytest` запускается
- [ ] Свободные 2 недели без других задач

### Опционально:
- [ ] Настроить Slack webhook для алертов
- [ ] Подготовить staging environment
- [ ] Уведомить команду о плане

---

## 📅 НЕДЕЛЯ 1: P0 КРИТИЧЕСКИЕ БЛОКЕРЫ

### День 1 (Пн): Security Hardening

**Утро (3 часа):**
```bash
# 1. Отозвать старые ключи (через веб-интерфейсы провайдеров)
# 2. Сгенерировать новые
# 3. Обновить .env (не коммитить!)

# Скрипт для генерации паролей:
openssl rand -hex 32  # для SECRET_KEY
openssl rand -base64 32 | tr -d "=+//" | cut -c1-32  # для NEO4J_PASSWORD
```

**День (3 часа):**
```bash
# Тесты безопасности
bandit -r src/ -f json -o bandit_report.json
safety check --json > safety_report.json

# Проверить что новые ключи работают:
python -c "from src.api.config import settings; print(settings.DEEPSEEK_API_KEY[:10])"
```

**Вечер:**
```bash
git add docs/security/
git commit -m "security: rotate all API keys and passwords"
git tag security-hardening-v1
```

---

### День 2 (Вт): API Endpoints Testing

**Цель:** Покрыть 10 критических endpoint'ов

```python
# tests/integration/test_api_critical.py

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

# 1. Health check
@pytest.mark.critical
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# 2. Query endpoint (core functionality)
@pytest.mark.critical
@pytest.mark.realapi
def test_query_endpoint():
    response = client.post("/api/query", json={
        "query": "Calculate Sharpe ratio for AAPL"
    })
    assert response.status_code == 200
    assert "result" in response.json()
    assert response.json()["disclaimer"]["version"] == "1.0"

# 3. Predictions API
@pytest.mark.critical
def test_predictions_list():
    response = client.get("/api/predictions")
    assert response.status_code == 200

# 4. WebSocket connection (Redis version)
@pytest.mark.critical
def test_websocket_connection():
    # Тестировать после реализации Redis
    pass
```

**Проверка вечером:**
```bash
pytest tests/integration/test_api_critical.py -v --cov=src.api.routes
# Ожидаем: +15% coverage
```

---

### День 3 (Ср): Real LLM Integration

**Цель:** Тесты с реальными LLM API

```python
# tests/integration/test_real_llm.py

import pytest
import os

# Пропускать если нет ключей
pytestmark = pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="No DEEPSEEK_API_KEY set"
)

class TestRealLLMIntegration:
    """Тесты с реальными LLM (стоят деньги!)"""
    
    def test_deepseek_simple_query(self):
        """Простой запрос к DeepSeek"""
        from src.orchestration.universal_llm_client import UniversalLLMClient
        
        client = UniversalLLMClient(provider="deepseek")
        result = client.generate("What is 2+2?")
        
        assert "4" in result or "four" in result.lower()
    
    def test_llm_fallback_chain(self):
        """Проверить fallback на другой провайдер"""
        # Симулировать отказ DeepSeek
        pass
```

**Важно:**
```bash
# Запускать только при наличии ключей:
export DEEPSEEK_API_KEY=sk-new-key-here
export ANTHROPIC_API_KEY=sk-ant-new-key-here

pytest tests/integration/test_real_llm.py -v
```

---

### День 4 (Чт): Config + Dependencies + Gaps

**Цель:** Покрыть оставшиеся критические модули

```python
# tests/unit/test_config.py

import pytest
from src.api.config import Settings

class TestConfig:
    """Configuration tests"""
    
    def test_production_settings_validation(self):
        """Production mode requires non-default secrets"""
        with pytest.raises(ValueError):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="dev_secret_key_change_in_production"
            )
    
    def test_database_connection_string(self):
        """Database URL constructed correctly"""
        settings = Settings()
        assert "postgresql" in str(settings.DATABASE_URL)
```

```python
# tests/unit/test_dependencies.py

import pytest
from src.api.dependencies import get_orchestrator

class TestDependencies:
    """Dependency injection tests"""
    
    def test_orchestrator_singleton(self):
        """Orchestrator should be singleton"""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2
```

**Проверка coverage:**
```bash
pytest --cov=src --cov-report=term
# Ожидаем: 75-80%
```

---

### День 5 (Пт): WebSocket → Redis

**Цель:** Миграция WebSocket на Redis

```python
# src/api/websocket_redis.py (каркас)

import redis
import json
from typing import Dict

class RedisConnectionManager:
    def __init__(self):
        self.redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=6379,
            decode_responses=True
        )
    
    async def connect(self, client_id: str, websocket):
        await websocket.accept()
        self.redis.hset("ws:connections", client_id, json.dumps({
            "connected_at": datetime.utcnow().isoformat()
        }))
    
    async def broadcast(self, message: str):
        self.redis.publish("ws:broadcast", message)
```

**Тест:**
```python
# tests/integration/test_websocket_redis.py

def test_connection_persists():
    """Connection survives server restart"""
    # 1. Подключить клиента
    # 2. Перезапустить сервер
    # 3. Проверить что клиент всё ещё в Redis
    pass
```

**Проверка:**
```bash
docker-compose up -d redis
# Запустить сервер
# Тестировать WebSocket через wscat
```

---

### День 6 (Пн, Week 2): WebSocket багфикс + Monitoring

**Утро (2 часа):** Багфикс WebSocket если есть проблемы

**День (6 часов):** Monitoring system

```python
# src/monitoring/system.py (каркас)

from prometheus_client import Counter, Histogram, Gauge

class MonitoringSystem:
    def __init__(self):
        self.queries = Counter('ape_queries_total', '', ['status'])
        self.accuracy = Gauge('ape_accuracy', '')
        self.latency = Histogram('ape_latency_seconds', '')
    
    def record_query(self, status: str, duration: float):
        self.queries.labels(status=status).inc()
        self.latency.observe(duration)
```

**Grafana dashboard:**
```json
{
  "title": "APE Production",
  "panels": [
    {"title": "Accuracy", "targets": [{"expr": "ape_accuracy"}]},
    {"title": "Query Rate", "targets": [{"expr": "rate(ape_queries_total[5m])"}]}
  ]
}
```

---

### День 7 (Вт): Alerting + Health Checks

**Цель:** Alerts + detailed health checks

```python
# src/api/health.py

@app.get("/health/detailed")
async def health_detailed():
    checks = {
        "postgres": await check_postgres(),
        "redis": await check_redis(),
        "deepseek": await check_deepseek(),
    }
    
    return {
        "status": "healthy" if all(c.status == "healthy" for c in checks.values()) else "degraded",
        "checks": checks
    }
```

**Alert rules:**
```yaml
# config/alerts.yml
groups:
  - name: ape_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(ape_queries_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
```

---

### День 8 (Ср): Circuit Breaker

**Цель:** Circuit breaker для LLM API

```python
# src/resilience/circuit_breaker.py

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = "closed"
        self.failures = 0
    
    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            raise CircuitBreakerOpen("Service unavailable")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

---

### День 9 (Чт): Code Sanitizer

**Цель:** Автоматическое исправление багов LLM кода

```python
# src/vee/code_sanitizer.py

class CodeSanitizer:
    def sanitize(self, code: str) -> str:
        # Fix 1: yfinance DataFrame
        code = code.replace(".history(...)", ".history(...).squeeze()")
        
        # Fix 2: Division by zero
        code = code.replace("/ divisor", "/ (divisor or 1e-10)")
        
        return code
```

**Тест на gs_005, gs_006:**
```bash
pytest tests/integration/test_golden_set_real_llm.py -k "gs_005 or gs_006"
# Ожидаем: PASS (если sanitizer работает)
```

---

### День 10 (Пт): Pre-production Checks

**Чеклист перед production:**

```bash
# 1. Security
bandit -r src/ -ll
# Ожидаем: 0 critical/high

# 2. Tests
pytest --cov=src --cov-fail-under=80
# Ожидаем: PASS

# 3. Golden Set
pytest tests/integration/test_golden_set_real_llm.py
# Ожидаем: 93.33%+

# 4. Health checks
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed

# 5. Metrics
curl http://localhost:8000/metrics

# 6. WebSocket (Redis)
wscat -c ws://localhost:8000/ws/test
```

---

## 📊 КОНТРОЛЬНЫЕ ТОЧКИ

### После Week 1 (Пт вечер):
- [ ] Coverage ≥ 75%
- [ ] Security scans clean
- [ ] WebSocket on Redis working
- [ ] All P0 issues resolved

### После Week 2 (Пт вечер):
- [ ] Coverage ≥ 80%
- [ ] Monitoring operational
- [ ] Circuit breaker tested
- [ ] Code sanitizer integrated
- [ ] Golden Set 93.33%+

---

## 🚨 ЭСКАЛАЦИЯ

Если что-то идёт не по плану:

### Coverage не растёт:
- Приоритет на критические модули
- Отложить debate system tests
- Цель: 75% (не 80%) acceptable

### WebSocket проблемы:
- Fallback на in-memory (с документацией)
- Отложить Redis на после production
- Не блокировать deploy

### gs_005/006 не фиксятся:
- 93.33% accuracy — acceptable
- 96.67% — nice to have
- Не блокировать production

---

## ✅ ГОТОВНОСТЬ К PRODUCTION

**Минимальные критерии:**
- Security: Все ключи rotated, scans clean
- Testing: Coverage ≥ 75%, critical paths covered
- Monitoring: Metrics + health checks работают
- Golden Set: 90%+ (лучше 93.33%)

**Ideal:**
- Coverage ≥ 80%
- Golden Set 93.33%+
- Circuit breaker implemented
- Code sanitizer working

---

## 🎯 СТАРТУЕМ!

**Сегодня:**
1. Отозвать API ключи
2. Сгенерировать новые
3. Запустить `docker-compose up -d`
4. Начать Day 1 tasks

**Удачи!** 🚀
