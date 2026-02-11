"""
Predictions module for APE 2026.

Handles storage and retrieval of price predictions and track record.
"""

from .prediction_store import PredictionStore, Prediction, PredictionCreate, TrackRecord, CorridorData
from .accuracy_tracker import AccuracyTracker
from .calibration import CalibrationTracker, CalibrationPoint
from .conformal import (
    ConformalPredictor,
    FinancialConformalPredictor,
    ConformalInterval,
    ConformalMethod
)
from .conformal_integration import (
    add_conformal_interval,
    get_calibration_residuals,
    evaluate_conformal_coverage
)

__all__ = [
    "PredictionStore",
    "Prediction",
    "PredictionCreate",
    "TrackRecord",
    "CorridorData",
    "AccuracyTracker",
    "CalibrationTracker",
    "CalibrationPoint",
    "ConformalPredictor",
    "FinancialConformalPredictor",
    "ConformalInterval",
    "ConformalMethod",
    "add_conformal_interval",
    "get_calibration_residuals",
    "evaluate_conformal_coverage",
]
