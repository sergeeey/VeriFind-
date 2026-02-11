"""Unit tests for multi-ticker comparison API endpoint."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import analysis as analysis_routes


class _FakeOrchestrator:
    """Fake orchestrator with per-ticker behavior."""

    async def process_query_async(self, query_id, query_text, provider=None, context=None):
        ticker = (context or {}).get("ticker", "UNKNOWN")
        if ticker == "MSFT":
            raise RuntimeError("synthetic failure for MSFT")

        score = {
            "AAPL": 0.81,
            "GOOGL": 0.77,
            "TSLA": 0.66,
        }.get(ticker, 0.5)

        return {
            "status": "completed",
            "answer": f"Result for {ticker}",
            "verification_score": score,
            "cost_usd": 0.01,
            "tokens_used": 100,
        }


def test_compare_endpoint_success_all_tickers(monkeypatch):
    class _AllSuccessOrchestrator:
        async def process_query_async(self, query_id, query_text, provider=None, context=None):
            ticker = (context or {}).get("ticker", "UNKNOWN")
            score = {"AAPL": 0.81, "GOOGL": 0.77}.get(ticker, 0.5)
            return {
                "status": "completed",
                "answer": f"Result for {ticker}",
                "verification_score": score,
                "cost_usd": 0.01,
                "tokens_used": 100,
            }

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(analysis_routes, "get_orchestrator", lambda provider=None: _AllSuccessOrchestrator())

    client = TestClient(app)
    response = client.post(
        "/api/compare",
        json={
            "query": "Compare Sharpe ratio for {ticker} in 2023",
            "tickers": ["AAPL", "GOOGL"],
            "provider": "openai",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "completed"
    assert body["provider"] == "openai"
    assert body["detected_language"] == "en"
    assert body["completed_count"] == 2
    assert body["failed_count"] == 0
    assert body["leader_ticker"] == "AAPL"
    assert body["total_tokens_used"] == 200
    assert body["pipeline_path"]["production_path"] == "langgraph"
    assert body["pipeline_path"]["bypasses"] == []
    assert all(item["detected_language"] == "en" for item in body["results"])


def test_compare_endpoint_partial_failure(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(analysis_routes, "get_orchestrator", lambda provider=None: _FakeOrchestrator())

    client = TestClient(app)
    response = client.post(
        "/api/compare",
        json={
            "query": "Compare risk profile for {ticker}",
            "tickers": ["AAPL", "MSFT", "GOOGL"],
            "provider": "openai",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "partial_failed"
    assert body["completed_count"] == 2
    assert body["failed_count"] == 1
    assert body["leader_ticker"] == "AAPL"
    msft_row = next(row for row in body["results"] if row["ticker"] == "MSFT")
    assert msft_row["status"] == "failed"
    assert "synthetic failure" in msft_row["error"]


def test_compare_endpoint_detects_russian_language(monkeypatch):
    class _RuOrchestrator:
        async def process_query_async(self, query_id, query_text, provider=None, context=None):
            ticker = (context or {}).get("ticker", "UNKNOWN")
            return {
                "status": "completed",
                "answer": f"Результат для {ticker}",
                "verification_score": 0.7,
                "cost_usd": 0.01,
                "tokens_used": 50,
            }

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(analysis_routes, "get_orchestrator", lambda provider=None: _RuOrchestrator())

    client = TestClient(app)
    response = client.post(
        "/api/compare",
        json={
            "query": "Сравни риск-профиль для {ticker}",
            "tickers": ["AAPL", "MSFT"],
            "provider": "openai",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["detected_language"] == "ru"
    assert all(item["detected_language"] == "ru" for item in body["results"])


def test_compare_endpoint_fail_closed_when_provider_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def _fail_if_called(provider=None):
        raise AssertionError("get_orchestrator must not be called when API key is missing")

    monkeypatch.setattr(analysis_routes, "get_orchestrator", _fail_if_called)

    client = TestClient(app)
    response = client.post(
        "/api/compare",
        json={
            "query": "Compare valuation for {ticker}",
            "tickers": ["AAPL", "MSFT"],
            "provider": "openai",
        },
    )

    assert response.status_code == 400
    assert "OPENAI_API_KEY is required" in response.json()["detail"]
