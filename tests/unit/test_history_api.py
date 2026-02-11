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


def test_export_history_json(monkeypatch):
    class FakeStore:
        def get_history(self, limit=100, ticker=None):
            return [
                {
                    "id": "q1",
                    "created_at": "2026-02-11T10:00:00Z",
                    "query_text": "Analyze AAPL",
                    "status": "completed",
                    "result_summary": "ok",
                    "confidence_score": 0.8,
                    "ticker_mentions": ["AAPL"],
                }
            ]

    monkeypatch.setattr(history_module, "get_history_store", lambda: FakeStore())
    client = _client()
    response = client.get("/api/history/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment; filename=query_history_export.json" in response.headers["content-disposition"]
    body = response.json()
    assert body["export_type"] == "query_history"
    assert body["count"] == 1


def test_export_history_csv(monkeypatch):
    class FakeStore:
        def get_history(self, limit=100, ticker=None):
            return [
                {
                    "id": "q1",
                    "created_at": "2026-02-11T10:00:00Z",
                    "query_text": "Analyze AAPL",
                    "status": "completed",
                    "result_summary": "ok",
                    "confidence_score": 0.8,
                    "ticker_mentions": ["AAPL", "MSFT"],
                }
            ]

    monkeypatch.setattr(history_module, "get_history_store", lambda: FakeStore())
    client = _client()
    response = client.get("/api/history/export?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=query_history_export.csv" in response.headers["content-disposition"]
    assert "id,created_at,query_text,status,result_summary,confidence_score,ticker_mentions" in response.text
    assert "AAPL,MSFT" in response.text
