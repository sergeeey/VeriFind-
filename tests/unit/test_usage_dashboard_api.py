"""Unit tests for API usage dashboard and middleware rate limiting behavior."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.middleware import rate_limit as rate_limit_module


def _client() -> TestClient:
    return TestClient(app)


def test_usage_summary_masks_api_keys(monkeypatch):
    rate_limit_module._reset_rate_limit_state_for_tests()
    monkeypatch.setenv("RATE_LIMIT_ENFORCEMENT", "false")

    client = _client()
    key = "dev_key_12345"

    client.get("/health", headers={"X-API-Key": key})
    client.get("/health", headers={"X-API-Key": key})

    response = client.get("/api/usage/summary")
    assert response.status_code == 200
    body = response.json()

    consumers = body["usage"]["consumers"]
    assert consumers, "Expected at least one tracked consumer"
    masked = consumers[0]["consumer"]
    assert "dev_key_12345" not in masked
    assert masked.startswith("key:")
    assert "..." in masked


def test_rate_limit_headers_change_with_usage(monkeypatch):
    rate_limit_module._reset_rate_limit_state_for_tests()
    monkeypatch.setenv("RATE_LIMIT_ENFORCEMENT", "false")

    client = _client()
    key = "dev_key_12345"

    r1 = client.get("/health", headers={"X-API-Key": key})
    r2 = client.get("/health", headers={"X-API-Key": key})

    assert r1.status_code == 200
    assert r2.status_code == 200

    rem1 = int(r1.headers["X-RateLimit-Remaining"])
    rem2 = int(r2.headers["X-RateLimit-Remaining"])
    assert rem2 <= rem1


def test_rate_limit_enforcement_returns_429(monkeypatch):
    rate_limit_module._reset_rate_limit_state_for_tests()
    monkeypatch.setenv("RATE_LIMIT_ENFORCEMENT", "true")

    # Tighten default limit for deterministic test.
    monkeypatch.setattr(rate_limit_module.settings, "default_rate_limit", 1)

    client = _client()
    key = "unknown_key_for_test"

    first = client.get("/health", headers={"X-API-Key": key})
    second = client.get("/health", headers={"X-API-Key": key})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"] == "Rate limit exceeded"
