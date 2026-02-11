"""
Integration helpers for Conformal Prediction with Prediction Store.

Week 13 Day 2: Bridge between conformal prediction and storage.
"""

from decimal import Decimal
from typing import Optional, List, Tuple
import logging

from .conformal import (
    FinancialConformalPredictor,
    ConformalInterval,
    ConformalMethod
)
from .prediction_store import PredictionCreate, PredictionStore

logger = logging.getLogger(__name__)


def add_conformal_interval(
    prediction_data: PredictionCreate,
    calibration_residuals: List[float],
    features: Optional[dict] = None,
    coverage_level: float = 0.95,
    method: ConformalMethod = ConformalMethod.NAIVE_ASYMMETRIC
) -> PredictionCreate:
    """
    Add conformal prediction interval to prediction data.

    Args:
        prediction_data: Base prediction (with price_base as point estimate)
        calibration_residuals: Historical residuals for calibration
        features: Optional features (volatility, etc.)
        coverage_level: Target coverage (default: 0.95)
        method: Conformal method to use

    Returns:
        Updated prediction_data with conformal intervals
    """
    # Create predictor
    predictor = FinancialConformalPredictor(
        coverage_level=coverage_level,
        method=method,
        volatility_adjustment=True
    )

    # Fit on calibration data
    predictor.fit(calibration_residuals)

    # Predict interval for point estimate
    point_estimate = float(prediction_data.price_base)
    interval = predictor.predict(point_estimate, features)

    # Update prediction data with conformal intervals
    prediction_data.lower_bound = Decimal(str(round(interval.lower_bound, 4)))
    prediction_data.upper_bound = Decimal(str(round(interval.upper_bound, 4)))
    prediction_data.interval_width = Decimal(str(round(interval.width, 4)))
    prediction_data.coverage_level = coverage_level
    prediction_data.conformal_method = method.value

    logger.info(
        f"Added conformal interval: [{interval.lower_bound:.2f}, {interval.upper_bound:.2f}] "
        f"(width={interval.width:.2f}, method={method.value})"
    )

    return prediction_data


def get_calibration_residuals(
    prediction_store: PredictionStore,
    ticker: Optional[str] = None,
    n_recent: int = 100
) -> List[float]:
    """
    Get historical residuals for calibration.

    Args:
        prediction_store: PredictionStore instance
        ticker: Specific ticker (None = all tickers)
        n_recent: Number of recent predictions to use

    Returns:
        List of residuals (actual - predicted)
    """
    # Get recent predictions with actual results
    predictions = prediction_store.get_recent_completed(
        limit=n_recent,
        ticker=ticker
    )

    # Calculate residuals
    residuals = []
    for pred in predictions:
        if pred.actual_price is not None:
            residual = float(pred.actual_price - pred.price_base)
            residuals.append(residual)

    if len(residuals) < 10:
        logger.warning(
            f"Only {len(residuals)} residuals available for calibration. "
            "Recommend at least 30 for reliable intervals."
        )

    return residuals


def evaluate_conformal_coverage(
    prediction_store: PredictionStore,
    ticker: Optional[str] = None,
    n_recent: int = 50
) -> dict:
    """
    Evaluate conformal prediction coverage on recent predictions.

    Args:
        prediction_store: PredictionStore instance
        ticker: Specific ticker (None = all tickers)
        n_recent: Number of recent predictions to evaluate

    Returns:
        Dict with coverage metrics
    """
    # Get predictions with conformal intervals and actual results
    predictions = prediction_store.get_recent_completed(
        limit=n_recent,
        ticker=ticker
    )

    # Filter predictions that have conformal intervals
    conformal_preds = [
        p for p in predictions
        if p.lower_bound is not None and p.upper_bound is not None
    ]

    if not conformal_preds:
        return {
            'error': 'No predictions with conformal intervals found',
            'n_evaluated': 0
        }

    # Calculate coverage
    covered = 0
    widths = []

    for pred in conformal_preds:
        if pred.actual_price is not None:
            # Check if actual price is within interval
            if pred.lower_bound <= pred.actual_price <= pred.upper_bound:
                covered += 1

            # Track interval width
            width = float(pred.upper_bound - pred.lower_bound)
            widths.append(width)

    n_evaluated = len(conformal_preds)
    coverage = covered / n_evaluated if n_evaluated > 0 else 0.0

    # Get target coverage from first prediction (should be same for all)
    target_coverage = conformal_preds[0].coverage_level or 0.95

    import statistics
    avg_width = statistics.mean(widths) if widths else 0.0
    median_width = statistics.median(widths) if widths else 0.0

    return {
        'n_evaluated': n_evaluated,
        'n_covered': covered,
        'coverage': coverage,
        'target_coverage': target_coverage,
        'coverage_gap': abs(coverage - target_coverage),
        'avg_width': avg_width,
        'median_width': median_width,
        'method': conformal_preds[0].conformal_method if conformal_preds else None
    }
