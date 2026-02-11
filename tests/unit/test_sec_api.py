"""Unit tests for SEC filings API route."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import sec as sec_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(sec_module.router)
    return TestClient(app)


def test_get_recent_filings_success(monkeypatch):
    monkeypatch.setattr(sec_module, "_lookup_cik", lambda ticker: "320193")
    monkeypatch.setattr(
        sec_module,
        "_fetch_submissions",
        lambda cik: {
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q", "8-K"],
                    "accessionNumber": ["0001-0001", "0002-0002", "0003-0003"],
                    "filingDate": ["2026-01-10", "2025-10-10", "2025-09-01"],
                    "reportDate": ["2025-09-30", "2025-06-30", "2025-08-31"],
                    "primaryDocument": ["a10k.htm", "a10q.htm", "a8k.htm"],
                }
            }
        },
    )

    client = _client()
    response = client.get("/api/sec/filings/AAPL?form=10-K&limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["count"] == 1
    assert body["filings"][0]["form"] == "10-K"
    assert "Archives/edgar/data" in body["filings"][0]["filing_url"]


def test_get_recent_filings_not_found(monkeypatch):
    monkeypatch.setattr(sec_module, "_lookup_cik", lambda ticker: None)
    client = _client()

    response = client.get("/api/sec/filings/UNKNOWN")
    assert response.status_code == 404
    assert "CIK not found" in response.json()["detail"]

