"""Unit tests for report generation API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import report as report_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(report_module.router)
    return TestClient(app)


def test_get_query_report_json(monkeypatch):
    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return {
                "episode": {"episode_id": query_id, "query_text": "Analyze AAPL"},
                "verified_fact": {
                    "fact_id": "fact_1",
                    "status": "success",
                    "confidence_score": 0.82,
                    "data_source": "yfinance",
                    "code_hash": "abc123",
                    "execution_time_ms": 123,
                    "memory_used_mb": 45.0,
                },
                "synthesis": {
                    "synthesis_id": "syn_1",
                    "original_confidence": 0.8,
                    "adjusted_confidence": 0.82,
                    "key_risks": ["volatility"],
                    "key_opportunities": ["growth"],
                },
            }

    monkeypatch.setattr(report_module, "get_graph_client", lambda: FakeGraphClient())
    client = _client()
    response = client.get("/api/report/query_1?format=json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment; filename=report_query_1.json" in response.headers["content-disposition"]
    body = response.json()
    assert body["query_id"] == "query_1"
    assert body["verification_score"] == 0.82


def test_get_query_report_markdown(monkeypatch):
    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return {
                "episode": {"episode_id": query_id, "query_text": "Analyze TSLA"},
                "verified_fact": {"status": "success", "confidence_score": 0.7, "code_hash": "hash1"},
                "synthesis": {"key_risks": ["valuation"], "key_opportunities": ["momentum"]},
            }

    monkeypatch.setattr(report_module, "get_graph_client", lambda: FakeGraphClient())
    client = _client()
    response = client.get("/api/report/query_2?format=md")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment; filename=report_query_2.md" in response.headers["content-disposition"]
    assert "# Analysis Report" in response.text

