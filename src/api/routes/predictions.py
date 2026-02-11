"""
Prediction Dashboard API routes.

Week 9 Day 3 - Prediction Dashboard Backend
Endpoints for retrieving predictions, track record, and corridor data.
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional, Dict, Any
from decimal import Decimal
from uuid import UUID
import logging

from pydantic import BaseModel, Field

from ...predictions import (
    PredictionStore,
    Prediction,
    TrackRecord,
    CorridorData,
    AccuracyTracker,
    CalibrationTracker,
)
from ..config import get_settings

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])
settings = get_settings()
logger = logging.getLogger(__name__)

# Disclaimer text
DISCLAIMER = (
    "This analysis is for informational and educational purposes only. "
    "NOT financial advice. NOT a recommendation to buy or sell securities. "
    "Past performance does not guarantee future results. "
    "Always consult a licensed financial advisor before making investment decisions."
)


# =============================================================================
# Response Models (with disclaimer)
# =============================================================================

class PredictionsListResponse(BaseModel):
    """Response for predictions list endpoint."""
    predictions: List[Prediction]
    total: int
    ticker: Optional[str] = None
    disclaimer: str = Field(default=DISCLAIMER)


class LatestPredictionResponse(BaseModel):
    """Response for latest prediction endpoint."""
    prediction: Optional[Prediction]
    disclaimer: str = Field(default=DISCLAIMER)


class PredictionHistoryResponse(BaseModel):
    """Response for prediction history endpoint."""
    ticker: str
    total: int
    predictions: List[Prediction]
    disclaimer: str = Field(default=DISCLAIMER)


class CorridorResponse(BaseModel):
    """Response for corridor visualization endpoint."""
    ticker: str
    corridor_data: List[CorridorData]
    disclaimer: str = Field(default=DISCLAIMER)


class TrackRecordResponse(BaseModel):
    """Response for track record endpoint."""
    track_record: TrackRecord
    disclaimer: str = Field(default=DISCLAIMER)


class TickersResponse(BaseModel):
    """Response for tickers list endpoint."""
    tickers: List[str]
    total: int
    disclaimer: str = Field(default=DISCLAIMER)


class CheckActualsResponse(BaseModel):
    """Response for check-actuals endpoint."""
    total_checked: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
    disclaimer: str = Field(default=DISCLAIMER)


class EvaluatePredictionResponse(BaseModel):
    """Response for evaluate single prediction endpoint."""
    success: bool
    result: Dict[str, Any]
    disclaimer: str = Field(default=DISCLAIMER)


class CalibrationResponse(BaseModel):
    """Response for prediction confidence calibration endpoint."""
    calibration_period: str
    total_evaluated: int
    expected_calibration_error: float
    brier_score: float
    calibration_curve: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    status: str = "ok"
    min_required_samples: int = 10
    ticker: Optional[str] = None
    disclaimer: str = Field(default=DISCLAIMER)


# =============================================================================
# Dependency: PredictionStore instance
# =============================================================================

def get_prediction_store() -> PredictionStore:
    """Get PredictionStore instance."""
    return PredictionStore(db_url=settings.timescaledb_url)


def _db_available() -> bool:
    """Check if database is available (for graceful degradation)."""
    try:
        import psycopg2
        # Try a quick connection
        conn = psycopg2.connect(settings.timescaledb_url, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


def get_accuracy_tracker(
    store: PredictionStore = Depends(get_prediction_store)
) -> AccuracyTracker:
    """Get AccuracyTracker instance."""
    return AccuracyTracker(prediction_store=store)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/", response_model=PredictionsListResponse)
async def get_predictions_list(
    ticker: Optional[str] = Query(default=None, description="Filter by ticker"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum predictions to return"),
    store: PredictionStore = Depends(get_prediction_store)
):
    """
    Get list of all predictions, optionally filtered by ticker.
    
    Args:
        ticker: Optional ticker symbol to filter by
        limit: Maximum number of predictions to return
        
    Returns:
        List of predictions
    """
    # Graceful degradation if DB unavailable
    if not _db_available():
        return PredictionsListResponse(predictions=[], total=0, ticker=ticker)
    
    try:
        if ticker:
            ticker = ticker.upper()
            predictions = store.get_prediction_history(ticker=ticker, limit=limit)
        else:
            # Get all predictions (from all tickers)
            all_tickers = store.get_all_tickers()
            predictions = []
            for t in all_tickers[:10]:  # Limit to avoid too many queries
                preds = store.get_prediction_history(ticker=t, limit=limit // len(all_tickers) or 1)
                predictions.extend(preds)
            # Sort by created_at descending
            predictions.sort(key=lambda p: p.created_at, reverse=True)
            predictions = predictions[:limit]
        
        return PredictionsListResponse(
            predictions=predictions,
            total=len(predictions),
            ticker=ticker
        )
        
    except Exception as e:
        logger.warning(f"Failed to retrieve predictions: {e}")
        # Return empty list instead of 500
        return PredictionsListResponse(predictions=[], total=0, ticker=ticker)


@router.get("/{ticker}/latest", response_model=LatestPredictionResponse)
async def get_latest_prediction(
    ticker: str,
    store: PredictionStore = Depends(get_prediction_store)
):
    """
    Get most recent prediction for ticker.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, TSLA)

    Returns:
        Latest prediction or null if none exists

    Example:
        GET /api/predictions/AAPL/latest
    """
    ticker = ticker.upper()

    try:
        prediction = store.get_latest_prediction(ticker)
        return LatestPredictionResponse(prediction=prediction)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve prediction: {str(e)}"
        )


@router.get("/{ticker}/history", response_model=PredictionHistoryResponse)
async def get_prediction_history(
    ticker: str,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum predictions to return"),
    include_pending: bool = Query(default=True, description="Include predictions without results"),
    store: PredictionStore = Depends(get_prediction_store)
):
    """
    Get historical predictions for ticker.

    Args:
        ticker: Stock ticker symbol
        limit: Max predictions to return (1-100)
        include_pending: Include predictions without actual results

    Returns:
        List of predictions ordered by created_at DESC

    Example:
        GET /api/predictions/AAPL/history?limit=10&include_pending=false
    """
    ticker = ticker.upper()

    # Graceful degradation if DB unavailable
    if not _db_available():
        return PredictionHistoryResponse(ticker=ticker, total=0, predictions=[])

    try:
        predictions = store.get_prediction_history(
            ticker=ticker,
            limit=limit,
            include_pending=include_pending
        )

        return PredictionHistoryResponse(
            ticker=ticker,
            total=len(predictions),
            predictions=predictions
        )

    except Exception as e:
        logger.warning(f"Failed to retrieve history: {e}")
        return PredictionHistoryResponse(ticker=ticker, total=0, predictions=[])


@router.get("/{ticker}/corridor", response_model=CorridorResponse)
async def get_corridor_data(
    ticker: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent predictions"),
    store: PredictionStore = Depends(get_prediction_store)
):
    """
    Get price corridor visualization data.

    Returns data for charting:
    - Prediction date
    - Target date
    - Price corridor (low/base/high)
    - Actual price (if available)
    - Whether prediction was a hit

    Args:
        ticker: Stock ticker symbol
        limit: Number of recent predictions (1-50)

    Returns:
        Corridor data for visualization

    Example:
        GET /api/predictions/AAPL/corridor?limit=5
    """
    ticker = ticker.upper()

    # Graceful degradation if DB unavailable
    if not _db_available():
        return CorridorResponse(ticker=ticker, corridor_data=[])

    try:
        corridor_data = store.get_corridor_data(ticker=ticker, limit=limit)

        return CorridorResponse(
            ticker=ticker,
            corridor_data=corridor_data
        )

    except Exception as e:
        logger.warning(f"Failed to retrieve corridor data: {e}")
        return CorridorResponse(ticker=ticker, corridor_data=[])


@router.get("/track-record", response_model=TrackRecordResponse)
async def get_track_record(
    ticker: Optional[str] = Query(default=None, description="Filter by ticker (optional)"),
    store: PredictionStore = Depends(get_prediction_store)
):
    """
    Get prediction accuracy statistics.

    Returns:
    - Total/completed/pending predictions
    - Hit/near/miss rates
    - Average/median error
    - Per-ticker statistics
    - Recent accuracy (last 10 predictions)

    Args:
        ticker: Optional ticker to filter by (default: all tickers)

    Returns:
        Track record statistics

    Example:
        GET /api/predictions/track-record
        GET /api/predictions/track-record?ticker=AAPL
    """
    if ticker:
        ticker = ticker.upper()

    # Graceful degradation if DB unavailable
    if not _db_available():
        from ...predictions import TrackRecord
        empty_record = TrackRecord(
            total_predictions=0,
            completed_predictions=0,
            pending_predictions=0,
            hit_rate=0.0,
            near_rate=0.0,
            miss_rate=0.0,
            avg_error_pct=0.0,
            median_error_pct=0.0,
            by_ticker={},
            recent_accuracy=0.0
        )
        return TrackRecordResponse(track_record=empty_record)

    try:
        track_record = store.get_track_record(ticker=ticker)

        return TrackRecordResponse(track_record=track_record)

    except Exception as e:
        logger.warning(f"Failed to retrieve track record: {e}")
        from ...predictions import TrackRecord
        empty_record = TrackRecord(
            total_predictions=0,
            completed_predictions=0,
            pending_predictions=0,
            hit_rate=0.0,
            near_rate=0.0,
            miss_rate=0.0,
            avg_error_pct=0.0,
            median_error_pct=0.0,
            by_ticker={},
            recent_accuracy=0.0
        )
        return TrackRecordResponse(track_record=empty_record)


@router.get("/calibration", response_model=CalibrationResponse)
async def get_calibration_metrics(
    days: int = Query(default=30, ge=7, le=365, description="Calibration period in days"),
    ticker: Optional[str] = Query(default=None, description="Optional ticker filter"),
    min_samples: int = Query(default=10, ge=1, le=1000, description="Minimum samples required"),
    store: PredictionStore = Depends(get_prediction_store),
):
    """
    Get confidence calibration metrics for evaluated predictions.

    Returns Expected Calibration Error (ECE), Brier score, calibration curve and
    recommendation hints (over/underconfidence by confidence bins).
    """
    safe_ticker = ticker.upper() if ticker else None

    if not _db_available():
        return CalibrationResponse(
            calibration_period=f"{days} days",
            total_evaluated=0,
            expected_calibration_error=0.0,
            brier_score=0.0,
            calibration_curve=[],
            recommendations=[],
            status="db_unavailable",
            min_required_samples=min_samples,
            ticker=safe_ticker,
        )

    try:
        tracker = CalibrationTracker(prediction_store=store)
        summary = tracker.calculate_summary(
            days=days,
            ticker=safe_ticker,
            min_samples=min_samples,
        )
        return CalibrationResponse(
            ticker=safe_ticker,
            **summary,
        )
    except Exception as e:
        logger.warning(f"Failed to retrieve calibration metrics: {e}")
        return CalibrationResponse(
            calibration_period=f"{days} days",
            total_evaluated=0,
            expected_calibration_error=0.0,
            brier_score=0.0,
            calibration_curve=[],
            recommendations=[],
            status="error",
            min_required_samples=min_samples,
            ticker=safe_ticker,
        )


@router.get("/tickers", response_model=TickersResponse)
async def get_tickers(
    store: PredictionStore = Depends(get_prediction_store)
):
    """
    Get list of all tickers with predictions.

    Returns tickers ordered by most recent prediction.

    Returns:
        List of ticker symbols

    Example:
        GET /api/predictions/tickers
    """
    try:
        tickers = store.get_all_tickers()

        return TickersResponse(
            tickers=tickers,
            total=len(tickers)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tickers: {str(e)}"
        )


@router.post("/check-actuals", response_model=CheckActualsResponse)
async def check_actuals(
    days_until_target: int = Query(default=7, ge=1, le=30, description="Days window for pending predictions"),
    tracker: AccuracyTracker = Depends(get_accuracy_tracker)
):
    """
    Run daily accuracy check for all pending predictions with expired target dates.

    Fetches actual prices via yfinance and updates predictions with:
    - Actual price
    - Accuracy band (HIT/NEAR/MISS)
    - Error percentage
    - Error direction (OVER/UNDER/EXACT)

    Args:
        days_until_target: Days before/after target_date to consider (default: 7)

    Returns:
        Summary of checked predictions with individual results

    Example:
        POST /api/predictions/check-actuals?days_until_target=7
    """
    try:
        results = tracker.run_daily_check(days_until_target=days_until_target)

        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful

        return CheckActualsResponse(
            total_checked=len(results),
            successful=successful,
            failed=failed,
            results=results
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run daily check: {str(e)}"
        )


@router.post("/{prediction_id}/evaluate", response_model=EvaluatePredictionResponse)
async def evaluate_prediction(
    prediction_id: UUID,
    tracker: AccuracyTracker = Depends(get_accuracy_tracker)
):
    """
    Evaluate a single prediction by comparing with actual price.

    Fetches actual price for the prediction's target_date and updates:
    - Actual price
    - Accuracy band (HIT/NEAR/MISS)
    - Error percentage
    - Error direction

    Args:
        prediction_id: UUID of prediction to evaluate

    Returns:
        Evaluation result with accuracy metrics

    Raises:
        404: Prediction not found
        500: Evaluation failed

    Example:
        POST /api/predictions/550e8400-e29b-41d4-a716-446655440000/evaluate
    """
    try:
        result = tracker.evaluate_prediction(prediction_id)

        if not result['success']:
            if 'not found' in result.get('message', ''):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result['message']
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result['message']
                )

        return EvaluatePredictionResponse(
            success=result['success'],
            result=result
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate prediction: {str(e)}"
        )
