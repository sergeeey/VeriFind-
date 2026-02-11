"""Unit tests for async /api/query + /api/status lifecycle."""

import time

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.query_tracker import create_query_status, reset_query_status_for_tests
from src.api.routes import analysis as analysis_module


def _client() -> TestClient:
    return TestClient(app)


def _wait_for_status(client: TestClient, query_id: str, expected: str, timeout_s: float = 2.0):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        response = client.get(f"/api/status/{query_id}")
        if response.status_code == 200:
            last = response.json()
            if last.get("status") == expected:
                return last
        time.sleep(0.05)
    return last


def test_query_status_lifecycle_completed(monkeypatch):
    reset_query_status_for_tests()

    class FakeOrchestrator:
        async def process_query_async(self, query_id, query_text, provider=None, context=None):
            return {
                "query_id": query_id,
                "episode_id": query_id,
                "status": "completed",
                "answer": "done",
                "verified_fact": {"fact_id": "f1"},
                "verification_score": 0.91,
                "nodes_visited": ["PLAN", "VEE", "GATE", "DEBATE"],
            }

    monkeypatch.setattr(analysis_module, "get_orchestrator", lambda provider=None: FakeOrchestrator())

    client = _client()
    submit = client.post(
        "/api/query",
        json={"query": "Calculate Sharpe ratio for AAPL over the last 12 months"},
    )
    assert submit.status_code == 202
    query_id = submit.json()["query_id"]

    body = _wait_for_status(client, query_id, expected="completed", timeout_s=2.0)
    assert body is not None

    assert body["query_id"] == query_id
    assert body["status"] == "completed"
    assert body["state"] == "completed"
    assert body["progress"] == 1.0
    assert body["verified_facts_count"] == 1
    assert body["episode_id"] == query_id
    assert body["metadata"]["answer"] == "done"
    assert body["metadata"]["episode_id"] == query_id
    assert body["metadata"]["detected_language"] == "en"


def test_query_status_lifecycle_failed(monkeypatch):
    reset_query_status_for_tests()

    class FakeOrchestrator:
        async def process_query_async(self, query_id, query_text, provider=None, context=None):
            raise RuntimeError("simulated pipeline failure")

    monkeypatch.setattr(analysis_module, "get_orchestrator", lambda provider=None: FakeOrchestrator())

    client = _client()
    submit = client.post(
        "/api/query",
        json={"query": "Calculate volatility regime shift for TSLA in 2025"},
    )
    assert submit.status_code == 202
    query_id = submit.json()["query_id"]

    body = _wait_for_status(client, query_id, expected="failed", timeout_s=2.0)
    assert body is not None

    assert body["query_id"] == query_id
    assert body["status"] == "failed"
    assert body["state"] == "failed"
    assert body["current_node"] == "ERROR"
    assert "simulated pipeline failure" in (body["error"] or "")


def test_status_returns_unknown_for_missing_query():
    reset_query_status_for_tests()
    client = _client()

    response = client.get("/api/status/nonexistent-query-id")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "unknown"
    assert body["state"] == "pending"
    assert body["progress"] == 0.0
    assert body["verified_facts_count"] == 0
    assert body["episode_id"] is None


def test_status_list_returns_recent_entries():
    reset_query_status_for_tests()
    create_query_status(query_id="q-a", query_text="first", status="pending", progress=0.1)
    create_query_status(query_id="q-b", query_text="second", status="completed", progress=1.0)

    client = _client()
    response = client.get("/api/status?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert all("query_id" in row and "status" in row and "state" in row for row in body)


def test_status_list_supports_filters():
    reset_query_status_for_tests()
    create_query_status(query_id="q-a", query_text="Analyze AAPL", status="completed", progress=1.0)
    create_query_status(query_id="q-b", query_text="Analyze TSLA", status="failed", progress=0.1)
    create_query_status(query_id="q-c", query_text="Risk model AAPL", status="completed", progress=1.0)

    client = _client()
    completed_only = client.get("/api/status?limit=10&state=completed")
    assert completed_only.status_code == 200
    completed_body = completed_only.json()
    assert len(completed_body) == 2
    assert all(row["state"] == "completed" for row in completed_body)

    aapl_only = client.get("/api/status?limit=10&query=aapl")
    assert aapl_only.status_code == 200
    aapl_body = aapl_only.json()
    assert len(aapl_body) == 2
    assert all("aapl" in (row.get("query_text") or "").lower() for row in aapl_body)


def test_status_summary_aggregates_counts():
    reset_query_status_for_tests()
    create_query_status(query_id="q-a", query_text="Analyze AAPL", status="completed", progress=1.0)
    create_query_status(query_id="q-b", query_text="Analyze TSLA", status="failed", progress=0.2)
    create_query_status(query_id="q-c", query_text="Analyze MSFT", status="planning", progress=0.1)

    client = _client()
    response = client.get("/api/status-summary")
    assert response.status_code == 200
    body = response.json()

    assert body["total_tracked"] >= 3
    assert body["completed"] >= 1
    assert body["failed"] >= 1
    assert body["pending"] >= 1
    assert body["today_count"] >= 3
