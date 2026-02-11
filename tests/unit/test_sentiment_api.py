"""Unit tests for sentiment API route."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import sentiment as sentiment_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(sentiment_module.router)
    return TestClient(app)


def test_get_ticker_sentiment_success(monkeypatch):
    class FakeTicker:
        def __init__(self, ticker):
            self.ticker = ticker
            self.news = [
                {"title": "AAPL beats earnings with strong growth", "publisher": "X", "link": "http://x", "providerPublishTime": 1},
                {"title": "Analysts see downside risk after lawsuit", "publisher": "Y", "link": "http://y", "providerPublishTime": 2},
            ]

    monkeypatch.setattr(sentiment_module.yf, "Ticker", FakeTicker)
    client = _client()

    response = client.get("/api/sentiment/AAPL?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["count"] == 2
    assert body["method"] == "lexicon_headline_scoring_v1"
    assert len(body["items"]) == 2


def test_get_ticker_sentiment_not_found(monkeypatch):
    class FakeTicker:
        def __init__(self, ticker):
            self.ticker = ticker
            self.news = []

    monkeypatch.setattr(sentiment_module.yf, "Ticker", FakeTicker)
    client = _client()

    response = client.get("/api/sentiment/UNKNOWN")
    assert response.status_code == 404
    assert "No news found" in response.json()["detail"]

