"""Unit tests for educational mode API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import educational as educational_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(educational_module.router)
    return TestClient(app)


def test_explain_detects_known_terms():
    client = _client()
    response = client.post(
        "/api/educational/explain",
        json={"text": "Sharpe and beta improved while volatility declined."},
    )
    assert response.status_code == 200
    body = response.json()
    assert "sharpe" in body["detected_terms"]
    assert "beta" in body["detected_terms"]
    assert "volatility" in body["detected_terms"]
    assert "sharpe" in body["definitions"]


def test_explain_handles_unknown_text():
    client = _client()
    response = client.post(
        "/api/educational/explain",
        json={"text": "General commentary without explicit finance metrics."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["detected_terms"] == []
    assert any("No known educational terms detected" in item for item in body["limitations"])

