"""Unit tests for prediction scheduler."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.predictions.scheduler import PredictionScheduler
from src.api.routes.health import router as health_router


@pytest.mark.asyncio
async def test_scheduler_run_daily_check(monkeypatch):
    """Scheduler updates last run state and metrics payload."""

    class FakeStore:
        def __init__(self, db_url):
            self.db_url = db_url

    class FakeTracker:
        def __init__(self, prediction_store):
            self.prediction_store = prediction_store

        def run_daily_check(self, days_until_target=7):
            return [{"success": True}, {"success": False}]

    monkeypatch.setattr("src.predictions.scheduler.PredictionStore", FakeStore)
    monkeypatch.setattr("src.predictions.scheduler.AccuracyTracker", FakeTracker)

    scheduler = PredictionScheduler()
    summary = await scheduler.run_daily_check(db_url="postgresql://test", days_until_target=7)

    assert summary["checked"] == 2
    assert summary["successful"] == 1
    assert summary["failed"] == 1
    assert scheduler.last_run_at is not None


def test_scheduler_health_endpoint_available():
    """Health endpoint exposes scheduler status payload."""
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    response = client.get("/api/health/scheduler")
    assert response.status_code == 200
    body = response.json()
    assert "scheduler" in body
    assert "running" in body["scheduler"]


def test_alerts_scheduler_health_endpoint_available():
    """Health endpoint exposes alerts scheduler status payload."""
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    response = client.get("/api/health/alerts-scheduler")
    assert response.status_code == 200
    body = response.json()
    assert "scheduler" in body
    assert "running" in body["scheduler"]


def test_circuit_breakers_health_not_initialized(monkeypatch):
    """Circuit breaker health returns safe payload before orchestrator startup."""
    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    monkeypatch.setattr(
        "src.api.routes.health.get_orchestrator_instance",
        lambda: {"orchestrator": None, "provider": None},
    )

    response = client.get("/api/health/circuit-breakers")
    assert response.status_code == 200
    body = response.json()
    assert body["initialized"] is False
    assert body["breakers"] == {}


def test_circuit_breakers_health_with_stats(monkeypatch):
    """Circuit breaker health exposes breaker stats when orchestrator exists."""
    class FakeBreaker:
        def __init__(self, name):
            self.name = name

        def get_stats(self):
            return {
                "name": self.name,
                "state": "closed",
                "failure_count": 0,
                "total_calls": 10,
                "failure_rate": 0.0,
            }

    class FakeOrchestrator:
        market_data_breaker = FakeBreaker("market_data_fetch")
        llm_debate_breaker = FakeBreaker("llm_debate")

    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    monkeypatch.setattr(
        "src.api.routes.health.get_orchestrator_instance",
        lambda: {"orchestrator": FakeOrchestrator(), "provider": "deepseek"},
    )

    response = client.get("/api/health/circuit-breakers")
    assert response.status_code == 200
    body = response.json()
    assert body["initialized"] is True
    assert body["provider"] == "deepseek"
    assert body["breakers"]["market_data_fetch"]["name"] == "market_data_fetch"
    assert body["breakers"]["llm_debate"]["name"] == "llm_debate"
