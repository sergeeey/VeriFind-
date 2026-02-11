"""Unit tests for portfolio optimization API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np

from src.api.routes.portfolio import router as portfolio_router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(portfolio_router)
    return TestClient(app)


def _mock_price_data(tickers):
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    close_data = pd.DataFrame(
        {
            ticker: 100 + np.cumsum(np.random.normal(0.1, 1.0, len(dates)))
            for ticker in tickers
        },
        index=dates,
    )
    close_data.columns = pd.MultiIndex.from_product([["Close"], tickers])
    return close_data


def test_portfolio_optimize_success(monkeypatch):
    client = _build_client()

    def _fake_download(tickers, start, end, auto_adjust=True, progress=False):
        return _mock_price_data(tickers)

    monkeypatch.setattr("src.api.routes.portfolio.yf.download", _fake_download)

    payload = {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "objective": "max_sharpe",
        "risk_free_rate": 0.04,
        "frontier_points": 10,
    }
    response = client.post("/api/portfolio/optimize", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert "portfolio" in body
    assert "weights" in body["portfolio"]
    assert abs(sum(body["portfolio"]["weights"].values()) - 1.0) < 1e-3
    assert body["verified_fact"]["source"] == "portfolio_optimizer_execution"
    assert len(body["efficient_frontier"]) > 0


def test_portfolio_optimize_empty_data(monkeypatch):
    client = _build_client()

    def _fake_download(tickers, start, end, auto_adjust=True, progress=False):
        return pd.DataFrame()

    monkeypatch.setattr("src.api.routes.portfolio.yf.download", _fake_download)

    payload = {
        "tickers": ["AAPL", "MSFT"],
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
        "objective": "min_volatility",
    }
    response = client.post("/api/portfolio/optimize", json=payload)
    assert response.status_code == 400
    assert "No market data" in response.json()["detail"]
