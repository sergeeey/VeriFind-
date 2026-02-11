"""Unit tests for standalone debate API endpoint."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import analysis as analysis_routes
from src.orchestration.langgraph_orchestrator import StateStatus


class _Dumpable:
    """Simple helper for objects expected to provide model_dump()."""

    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return self._payload


class _FakeDebateAdapter:
    def get_stats(self):
        return {
            "total_cost": 0.123,
            "total_input_tokens": 111,
            "total_output_tokens": 222,
        }


class _FakeOrchestrator:
    def __init__(self, final_state):
        self.final_state = final_state
        self.debate_adapter = _FakeDebateAdapter()

    def run(self, query_id, query_text, direct_code, use_plan):
        return self.final_state


def test_debate_endpoint_returns_real_payload_and_provider(monkeypatch):
    final_state = SimpleNamespace(
        status=StateStatus.COMPLETED,
        error_message=None,
        debate_reports=[
            _Dumpable({"perspective": "bull", "key_points": ["strong revenue"]}),
            _Dumpable({"perspective": "bear", "key_points": ["high valuation"]}),
        ],
        synthesis=_Dumpable(
            {
                "balanced_view": "Mixed outlook with upside and valuation risk.",
                "adjusted_confidence": 0.81,
            }
        ),
        verified_fact=SimpleNamespace(
            fact_id="fact_1",
            statement="AAPL valuation is elevated",
            extracted_values={"metric": "pe_ratio", "value": 30.2},
            confidence_score=0.81,
            data_source="yfinance",
        ),
        nodes_visited=["PLAN", "FETCH", "VEE", "GATE", "DEBATE"],
    )
    fake_orchestrator = _FakeOrchestrator(final_state)
    captured = {}

    def _fake_get_orchestrator(provider=None):
        captured["provider"] = provider
        return fake_orchestrator

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(analysis_routes, "get_orchestrator", _fake_get_orchestrator)

    client = TestClient(app)
    response = client.post(
        "/api/debate",
        json={
            "query": "Analyze AAPL valuation risks and opportunities",
            "provider": "openai",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "debate_completed"
    assert body["provider"] == "openai"
    assert body["detected_language"] == "en"
    assert captured["provider"] == "openai"
    assert body["synthesis"]["balanced_view"].startswith("Mixed outlook")
    assert len(body["debate_reports"]) == 2
    assert body["cost_usd"] == 0.123
    assert body["tokens_used"] == 333


def test_debate_endpoint_fail_closed_when_provider_key_missing(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def _fail_if_called(provider=None):
        raise AssertionError("get_orchestrator must not be called when API key is missing")

    monkeypatch.setattr(analysis_routes, "get_orchestrator", _fail_if_called)

    client = TestClient(app)
    response = client.post(
        "/api/debate",
        json={
            "query": "Analyze TSLA risk profile for next quarter",
            "provider": "deepseek",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert "DEEPSEEK_API_KEY is required" in body["detail"]
