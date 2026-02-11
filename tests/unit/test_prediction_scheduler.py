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
