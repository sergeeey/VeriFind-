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


def test_get_verification_transparency_success(monkeypatch):
    """Returns normalized verification transparency payload."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return {
                "episode": {
                    "episode_id": query_id,
                    "query_text": "Analyze AAPL quality and valuation",
                },
                "verified_fact": {
                    "fact_id": "fact_001",
                    "code_hash": "hash_001",
                    "data_source": "yfinance",
                    "confidence_score": 0.82,
                },
                "synthesis": {
                    "synthesis_id": "syn_001",
                    "original_confidence": 0.78,
                    "adjusted_confidence": 0.82,
                    "confidence_rationale": "Debate improved confidence due to consensus.",
                    "debate_quality_score": 0.87,
                    "areas_of_agreement": ["Revenue growth is stable"],
                    "areas_of_disagreement": ["Valuation premium sustainability"],
                    "key_risks": ["Valuation compression"],
                    "key_opportunities": ["Margin expansion"],
                },
            }

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/verification/query_001")
    assert response.status_code == 200
    body = response.json()

    assert body["query_id"] == "query_001"
    assert body["verification_score"] == 0.82
    assert body["confidence_before"] == 0.78
    assert body["confidence_after"] == 0.82
    assert body["confidence_delta"] == 0.04
    assert "consensus" in body["confidence_rationale"].lower()
    assert body["debate_quality_score"] == 0.87
    assert body["provenance"]["fact_id"] == "fact_001"
    assert body["provenance"]["synthesis_id"] == "syn_001"


def test_get_verification_transparency_uses_raw_payload_fallback(monkeypatch):
    """Uses raw_payload fields when synthesis node is sparse."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return {
                "episode": {
                    "episode_id": query_id,
                    "query_text": "Analyze MSFT downside risk",
                },
                "verified_fact": {
                    "fact_id": "fact_002",
                    "confidence_score": 0.75,
                },
                "synthesis": {
                    "synthesis_id": "syn_002",
                    "raw_payload": {
                        "original_confidence": 0.80,
                        "adjusted_confidence": 0.75,
                        "confidence_rationale": "Bear arguments reduced confidence.",
                        "debate_quality_score": 0.66,
                        "key_risks": ["Demand slowdown"],
                        "areas_of_disagreement": ["Terminal growth assumptions"],
                    },
                },
            }

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/verification/query_002")
    assert response.status_code == 200
    body = response.json()

    assert body["verification_score"] == 0.75
    assert body["confidence_before"] == 0.80
    assert body["confidence_after"] == 0.75
    assert body["confidence_delta"] == -0.05
    assert body["debate_quality_score"] == 0.66
    assert body["key_risks"] == ["Demand slowdown"]
    assert body["areas_of_disagreement"] == ["Terminal growth assumptions"]


def test_get_verification_transparency_not_found(monkeypatch):
    """Returns 404 when verification trail is missing."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return None

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/verification/missing_query")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_verification_transparency_internal_error(monkeypatch):
    """Returns 500 on unexpected failures."""

    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()

    response = client.get("/api/verification/query_500")
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to retrieve verification transparency"


def test_export_audit_trail_json(monkeypatch):
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
                    "execution_time_ms": 100,
                    "memory_used_mb": 12.3,
                    "confidence_score": 0.82,
                    "data_source": "yfinance",
                },
                "synthesis": {
                    "synthesis_id": "syn_001",
                    "key_risks": ["volatility"],
                    "key_opportunities": ["growth"],
                    "original_confidence": 0.78,
                    "adjusted_confidence": 0.82,
                },
            }

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()
    response = client.get("/api/audit/query_001/export?format=json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment; filename=audit_query_001.json" in response.headers["content-disposition"]
    body = response.json()
    assert body["query_id"] == "query_001"
    assert body["trail"]["verified_fact"]["fact_id"] == "fact_001"


def test_export_audit_trail_csv(monkeypatch):
    class FakeGraphClient:
        def get_audit_trail(self, query_id):
            return {
                "episode": {
                    "episode_id": query_id,
                    "query_text": "Analyze TSLA risk",
                },
                "verified_fact": {
                    "fact_id": "fact_777",
                    "status": "success",
                    "code_hash": "hash777",
                    "confidence_score": 0.74,
                    "data_source": "yfinance",
                },
                "synthesis": {
                    "synthesis_id": "syn_777",
                    "key_risks": ["valuation"],
                    "key_opportunities": ["momentum"],
                    "original_confidence": 0.8,
                    "adjusted_confidence": 0.74,
                },
            }

    monkeypatch.setattr(audit_module, "get_graph_client", lambda: FakeGraphClient())
    client = _build_test_client()
    response = client.get("/api/audit/query_777/export?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=audit_query_777.csv" in response.headers["content-disposition"]
    assert "query_id,query_text,fact_id,verification_score" in response.text
    assert "query_777,Analyze TSLA risk,fact_777,0.74" in response.text
