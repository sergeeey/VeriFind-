"""Unit tests for prediction calibration pipeline."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import predictions as predictions_routes
from src.predictions.calibration import CalibrationTracker, CalibrationPoint
from src.predictions.scheduler import PredictionScheduler


def test_compute_calibration_curve():
    tracker = CalibrationTracker(prediction_store=None)
    points = [
        CalibrationPoint(confidence=0.2, outcome=0.0),
        CalibrationPoint(confidence=0.3, outcome=1.0),
        CalibrationPoint(confidence=0.8, outcome=1.0),
        CalibrationPoint(confidence=0.9, outcome=0.0),
    ]

    curve = tracker.compute_calibration_curve(points, bins=5)

    assert len(curve) == 5
    assert sum(item["count"] for item in curve) == len(points)
    assert all("predicted_prob" in item for item in curve)
    assert all("actual_accuracy" in item for item in curve)


def test_compute_brier_score():
    tracker = CalibrationTracker(prediction_store=None)
    points = [
        CalibrationPoint(confidence=0.9, outcome=1.0),
        CalibrationPoint(confidence=0.8, outcome=0.0),
    ]

    brier = tracker.compute_brier_score(points)

    assert brier == 0.325


def test_recommend_adjustments():
    tracker = CalibrationTracker(prediction_store=None)
    curve = [
        {"confidence_bin": "0.7-0.8", "predicted_prob": 0.75, "actual_accuracy": 0.55, "count": 12},
        {"confidence_bin": "0.2-0.3", "predicted_prob": 0.25, "actual_accuracy": 0.30, "count": 4},
    ]

    recs = tracker.recommend_adjustments(curve, min_count=5, threshold=0.05)

    assert len(recs) == 1
    assert recs[0]["issue"] == "overconfident"
    assert recs[0]["adjustment"] == -0.2


def test_calibration_api_endpoint(monkeypatch):
    class _FakeStore:
        pass

    class _FakeCalibrationTracker:
        def __init__(self, prediction_store):
            self.prediction_store = prediction_store

        def calculate_summary(self, days=30, ticker=None, min_samples=10):
            return {
                "calibration_period": f"{days} days",
                "total_evaluated": 42,
                "expected_calibration_error": 0.08,
                "brier_score": 0.12,
                "calibration_curve": [{"confidence_bin": "0.0-0.1", "predicted_prob": 0.05, "actual_accuracy": 0.02, "count": 10}],
                "recommendations": [{"bin": "0.7-0.8", "issue": "overconfident", "adjustment": -0.12, "message": "test"}],
                "status": "ok",
                "min_required_samples": min_samples,
            }

    monkeypatch.setattr(predictions_routes, "_db_available", lambda: True)
    monkeypatch.setattr(predictions_routes, "CalibrationTracker", _FakeCalibrationTracker)

    app.dependency_overrides[predictions_routes.get_prediction_store] = lambda: _FakeStore()
    try:
        client = TestClient(app)
        response = client.get("/api/predictions/calibration?days=30")
    finally:
        app.dependency_overrides.pop(predictions_routes.get_prediction_store, None)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["total_evaluated"] == 42
    assert body["expected_calibration_error"] == 0.08
    assert body["brier_score"] == 0.12


def test_calibration_with_no_data(monkeypatch):
    monkeypatch.setattr(predictions_routes, "_db_available", lambda: False)

    client = TestClient(app)
    response = client.get("/api/predictions/calibration?days=30")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "db_unavailable"
    assert body["total_evaluated"] == 0


@pytest.mark.asyncio
async def test_calibration_integration_with_scheduler(monkeypatch):
    class FakeStore:
        def __init__(self, db_url):
            self.db_url = db_url

    class FakeTracker:
        def __init__(self, prediction_store):
            self.prediction_store = prediction_store

        def run_daily_check(self, days_until_target=7):
            return [{"success": True}, {"success": False}]

    class FakeCalibration:
        def __init__(self, prediction_store):
            self.prediction_store = prediction_store

        def calculate_summary(self, days=30, min_samples=10):
            return {
                "status": "ok",
                "total_evaluated": 100,
                "expected_calibration_error": 0.04,
                "brier_score": 0.11,
            }

    monkeypatch.setattr("src.predictions.scheduler.PredictionStore", FakeStore)
    monkeypatch.setattr("src.predictions.scheduler.AccuracyTracker", FakeTracker)
    monkeypatch.setattr("src.predictions.scheduler.CalibrationTracker", FakeCalibration)

    scheduler = PredictionScheduler()
    summary = await scheduler.run_daily_check(db_url="postgresql://test")

    assert summary["checked"] == 2
    assert summary["successful"] == 1
    assert summary["failed"] == 1
    assert summary["calibration"]["status"] == "ok"
    assert summary["calibration"]["total_evaluated"] == 100
