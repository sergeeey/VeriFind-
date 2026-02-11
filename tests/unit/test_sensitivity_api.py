"""Unit tests for sensitivity analysis API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import sensitivity as sensitivity_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(sensitivity_module.router)
    return TestClient(app)


def test_price_sensitivity_with_explicit_base_price():
    client = _client()
    response = client.post(
        "/api/sensitivity/price",
        json={
            "ticker": "AAPL",
            "position_size": 10,
            "base_price": 100.0,
            "variation_pct": 10.0,
            "steps": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["base_price"] == 100.0
    assert body["steps"] == 5
    assert len(body["scenarios"]) == 5
    # Sweep includes negative and positive shocks -> sign flip expected.
    assert body["sign_flip_detected"] is True


def test_price_sensitivity_loads_base_price(monkeypatch):
    monkeypatch.setattr(sensitivity_module, "_load_base_price", lambda ticker: 123.45)
    client = _client()

    response = client.post(
        "/api/sensitivity/price",
        json={
            "ticker": "MSFT",
            "position_size": 5,
            "variation_pct": 5.0,
            "steps": 3,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["base_price"] == 123.45
    assert body["ticker"] == "MSFT"


def test_price_sensitivity_returns_404_when_base_unavailable(monkeypatch):
    monkeypatch.setattr(sensitivity_module, "_load_base_price", lambda ticker: None)
    client = _client()

    response = client.post(
        "/api/sensitivity/price",
        json={
            "ticker": "UNKNOWN",
            "position_size": 5,
            "variation_pct": 5.0,
            "steps": 3,
        },
    )
    assert response.status_code == 404
    assert "Unable to load base price" in response.json()["detail"]

