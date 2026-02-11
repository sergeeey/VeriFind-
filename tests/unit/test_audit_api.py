"""Unit tests for audit API route."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import audit as audit_module


def _build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(audit_module.router)
    return TestClient(app)


def test_get_audit_trail_success(monkeypatch):
    """Returns normalized audit trail payload."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return {
                "episode": {
                    "episode_id": query_id,
                    "query_text": "Analyze AAPL trend",
                },
                "verified_fact": {
                    "fact_id": "fact_001",
                    "status": "success",
                    "code_hash": "abc123",
                    "execution_time_ms": 1234,
                    "memory_used_mb": 45.6,
                    "source_code": "print('ok')",
                },
                "synthesis": {
                    "synthesis_id": "syn_001",
                    "key_risks": ["volatility"],
                    "key_opportunities": ["growth"],
                    "original_confidence": 0.8,
                    "adjusted_confidence": 0.82,
                },
            }

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/audit/query_001")
    assert response.status_code == 200
    body = response.json()
    assert body["query_id"] == "query_001"
    assert body["query_text"] == "Analyze AAPL trend"
    assert body["trail"]["execution"]["code_hash"] == "abc123"
    assert body["trail"]["debate"]["confidence_after"] == 0.82


def test_get_audit_trail_not_found(monkeypatch):
    """Returns 404 when audit trail is missing."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return None

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/audit/missing_query")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_audit_trail_internal_error(monkeypatch):
    """Returns 500 on unexpected backend failures."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/audit/query_500")
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to retrieve audit trail"


def test_get_audit_trail_redacts_secrets(monkeypatch):
    """Redacts likely secrets from returned source code."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return {
                "episode": {"episode_id": query_id, "query_text": "Secret test"},
                "verified_fact": {
                    "fact_id": "fact_secret",
                    "status": "success",
                    "code_hash": "hash_secret",
                    "source_code": "api_key='sk-SECRET-1234567890'",
                },
                "synthesis": {},
            }

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/audit/query_secret")
    assert response.status_code == 200
    code = response.json()["trail"]["plan"]["code"]
    assert "[REDACTED" in code
