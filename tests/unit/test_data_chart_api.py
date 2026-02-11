"""Unit tests for advanced chart data endpoint."""

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import data as data_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(data_module.router)
    return TestClient(app)


def test_get_advanced_chart_data_success(monkeypatch):
    index = pd.date_range("2026-01-01", periods=5, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104],
            "High": [101, 102, 103, 104, 105],
            "Low": [99, 100, 101, 102, 103],
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "Volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=index,
    )

    class FakeTicker:
        def __init__(self, ticker):
            self.ticker = ticker

        def history(self, period="6mo", interval="1d", auto_adjust=True):
            return frame

    monkeypatch.setattr(data_module.yf, "Ticker", FakeTicker)
    client = _client()

    response = client.get("/api/data/chart/AAPL?period=1mo&interval=1d")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["point_count"] == 5
    assert len(body["points"]) == 5
    assert body["indicators"]["ema_period"] == 20
    assert body["indicators"]["rsi_period"] == 14


def test_get_advanced_chart_data_not_found(monkeypatch):
    empty = pd.DataFrame()

    class FakeTicker:
        def __init__(self, ticker):
            self.ticker = ticker

        def history(self, period="6mo", interval="1d", auto_adjust=True):
            return empty

    monkeypatch.setattr(data_module.yf, "Ticker", FakeTicker)
    client = _client()

    response = client.get("/api/data/chart/UNKNOWN")
    assert response.status_code == 404
    assert "No chart data available" in response.json()["detail"]

