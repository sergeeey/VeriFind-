"""Unit tests for query history API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import history as history_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(history_module.router)
    return TestClient(app)


def test_get_history(monkeypatch):
    class FakeStore:
        def get_history(self, limit=20, ticker=None):
            return [{"id": "q1", "query_text": "AAPL analysis", "status": "completed"}]

    monkeypatch.setattr(history_module, "get_history_store", lambda: FakeStore())
    client = _client()
    response = client.get("/api/history?limit=10&ticker=AAPL")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "q1"


def test_search_history(monkeypatch):
    class FakeStore:
        def search_history(self, search_query, limit=20):
            return [{"id": "q2", "query_text": "sharpe ratio", "status": "completed"}]

    monkeypatch.setattr(history_module, "get_history_store", lambda: FakeStore())
    client = _client()
    response = client.get("/api/history/search?q=sharpe")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "q2"


def test_get_history_entry_not_found(monkeypatch):
    class FakeStore:
        def get_entry(self, query_id):
            return None

    monkeypatch.setattr(history_module, "get_history_store", lambda: FakeStore())
    client = _client()
    response = client.get("/api/history/missing")
    assert response.status_code == 404


def test_delete_history_entry(monkeypatch):
    class FakeStore:
        def delete_entry(self, query_id):
            return True

    monkeypatch.setattr(history_module, "get_history_store", lambda: FakeStore())
    client = _client()
    response = client.delete("/api/history/q1")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
