"""
Prediction Dashboard API routes.

Week 9 Day 3 - Prediction Dashboard Backend
Endpoints for retrieving predictions, track record, and corridor data.
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional, Dict, Any
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from ...predictions import PredictionStore, Prediction, TrackRecord, CorridorData, AccuracyTracker
from ..config import get_settings

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])
settings = get_settings()

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


# =============================================================================
# Dependency: PredictionStore instance
# =============================================================================

def get_prediction_store() -> PredictionStore:
    """Get PredictionStore instance."""
    return PredictionStore(db_url=settings.timescaledb_url)


def get_accuracy_tracker(
    store: PredictionStore = Depends(get_prediction_store)
) -> AccuracyTracker:
    """Get AccuracyTracker instance."""
    return AccuracyTracker(prediction_store=store)


# =============================================================================
# API Endpoints
# =============================================================================

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


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

    try:
        corridor_data = store.get_corridor_data(ticker=ticker, limit=limit)

        return CorridorResponse(
            ticker=ticker,
            corridor_data=corridor_data
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve corridor data: {str(e)}"
        )


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

    try:
        track_record = store.get_track_record(ticker=ticker)

        return TrackRecordResponse(track_record=track_record)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve track record: {str(e)}"
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
