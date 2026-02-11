"""Unit tests for price alerts API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import alerts as alerts_module


def _client() -> tuple[TestClient, FastAPI]:
    app = FastAPI()
    app.include_router(alerts_module.router)
    return TestClient(app), app


def test_create_price_alert(monkeypatch):
    class FakeStore:
        def create_alert(self, ticker, condition, target_price):
            return {
                "id": "a1",
                "ticker": ticker,
                "condition": condition,
                "target_price": target_price,
                "is_active": True,
                "created_at": "2026-02-11T10:00:00Z",
            }

    client, app = _client()
    app.dependency_overrides[alerts_module.get_alert_store] = lambda: FakeStore()
    try:
        response = client.post(
            "/api/alerts",
            json={"ticker": "AAPL", "condition": "above", "target_price": 200},
        )
    finally:
        app.dependency_overrides.pop(alerts_module.get_alert_store, None)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "a1"
    assert body["ticker"] == "AAPL"
    assert body["condition"] == "above"


def test_list_price_alerts(monkeypatch):
    class FakeStore:
        def list_alerts(self, ticker=None, active_only=True):
            return [
                {
                    "id": "a1",
                    "ticker": "AAPL",
                    "condition": "above",
                    "target_price": 200,
                    "is_active": True,
                    "last_notified_at": "2026-02-11T11:00:00Z",
                }
            ]

    client, app = _client()
    app.dependency_overrides[alerts_module.get_alert_store] = lambda: FakeStore()
    try:
        response = client.get("/api/alerts?ticker=AAPL")
    finally:
        app.dependency_overrides.pop(alerts_module.get_alert_store, None)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "AAPL"
    assert body[0]["last_notified_at"] == "2026-02-11T11:00:00Z"


def test_delete_price_alert(monkeypatch):
    class FakeStore:
        def delete_alert(self, alert_id):
            return True

    client, app = _client()
    app.dependency_overrides[alerts_module.get_alert_store] = lambda: FakeStore()
    try:
        response = client.delete("/api/alerts/a1")
    finally:
        app.dependency_overrides.pop(alerts_module.get_alert_store, None)
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_check_price_alerts(monkeypatch):
    class FakeStore:
        pass

    store = FakeStore()
    class FakeChecker:
        def __init__(self, store):
            self.store = store

        def check_active_alerts(self, ticker=None):
            return {
                "total_checked": 2,
                "triggered_count": 2,
                "notifications_sent": 1,
                "rows": [
                    {"id": "a1", "ticker": "AAPL", "condition": "above", "target_price": 200, "current_price": 210.0, "triggered": True},
                    {"id": "a2", "ticker": "MSFT", "condition": "below", "target_price": 300, "current_price": 295.0, "triggered": True},
                ],
            }

    monkeypatch.setattr(alerts_module, "PriceAlertChecker", FakeChecker)

    client, app = _client()
    app.dependency_overrides[alerts_module.get_alert_store] = lambda: store
    try:
        response = client.post("/api/alerts/check-now")
    finally:
        app.dependency_overrides.pop(alerts_module.get_alert_store, None)
    assert response.status_code == 200
    body = response.json()
    assert body["total_checked"] == 2
    assert body["triggered_count"] == 2
    assert body["notifications_sent"] == 1
