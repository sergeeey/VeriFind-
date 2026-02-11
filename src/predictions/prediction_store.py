"""
Prediction storage and retrieval for APE 2026.

Handles CRUD operations for price predictions in TimescaleDB.
Week 9 Day 3 - Prediction Dashboard Backend
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================

class PredictionCreate(BaseModel):
    """Request model for creating a new prediction."""
    ticker: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(default="US", max_length=20)
    horizon_days: int = Field(..., gt=0, description="Prediction horizon in days")
    target_date: date = Field(..., description="Target date for prediction")

    price_at_creation: Decimal = Field(..., gt=0, decimal_places=4)
    price_low: Decimal = Field(..., gt=0, decimal_places=4)
    price_base: Decimal = Field(..., gt=0, decimal_places=4)
    price_high: Decimal = Field(..., gt=0, decimal_places=4)

    reasoning: Dict[str, Any] = Field(..., description="Structured reasoning (JSONB)")
    verification_score: float = Field(..., ge=0.0, le=1.0)
    model_used: str = Field(..., max_length=50)
    pipeline_cost: Decimal = Field(..., ge=0, decimal_places=6)

    was_calibrated: bool = Field(default=False)
    calibration_adj: Optional[float] = Field(None, ge=-1.0, le=1.0)

    # Conformal Prediction intervals (Week 13)
    lower_bound: Optional[Decimal] = Field(None, description="Conformal lower bound")
    upper_bound: Optional[Decimal] = Field(None, description="Conformal upper bound")
    interval_width: Optional[Decimal] = Field(None, ge=0, description="Interval width")
    coverage_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="Target coverage (e.g., 0.95)")
    conformal_method: Optional[str] = Field(None, max_length=50, description="Conformal method used")

    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v):
        """Ensure reasoning contains required keys."""
        required_keys = ['summary', 'key_factors']
        for key in required_keys:
            if key not in v:
                raise ValueError(f"reasoning must contain '{key}' key")
        return v


class Prediction(BaseModel):
    """Complete prediction model with actual results."""
    id: UUID
    created_at: datetime
    ticker: str
    exchange: str
    horizon_days: int
    target_date: date

    # Price corridor
    price_at_creation: Decimal
    price_low: Decimal
    price_base: Decimal
    price_high: Decimal

    # Metadata
    reasoning: Dict[str, Any]
    verification_score: float
    model_used: str
    pipeline_cost: Decimal

    # Actual results (nullable until target_date)
    actual_price: Optional[Decimal] = None
    actual_date: Optional[date] = None
    accuracy_band: Optional[str] = None  # HIT, NEAR, MISS
    error_pct: Optional[float] = None
    error_direction: Optional[str] = None  # OVER, UNDER, EXACT

    # Calibration
    was_calibrated: bool
    calibration_adj: Optional[float] = None

    # Conformal Prediction intervals (Week 13)
    lower_bound: Optional[Decimal] = None
    upper_bound: Optional[Decimal] = None
    interval_width: Optional[Decimal] = None
    coverage_level: Optional[float] = None
    conformal_method: Optional[str] = None

    class Config:
        from_attributes = True


class TrackRecord(BaseModel):
    """Track record statistics for predictions."""
    total_predictions: int
    completed_predictions: int
    pending_predictions: int

    # Accuracy metrics
    hit_rate: float = Field(..., ge=0.0, le=1.0, description="% within corridor")
    near_rate: float = Field(..., ge=0.0, le=1.0, description="% close to corridor")
    miss_rate: float = Field(..., ge=0.0, le=1.0, description="% outside corridor")

    # Error metrics
    avg_error_pct: float
    median_error_pct: float

    # By ticker
    by_ticker: Dict[str, Dict[str, Any]]

    # Recent predictions
    recent_accuracy: float = Field(..., ge=0.0, le=1.0, description="Last 10 predictions accuracy")


class CorridorData(BaseModel):
    """Price corridor visualization data."""
    ticker: str
    prediction_date: datetime
    target_date: date

    price_at_creation: Decimal
    price_low: Decimal
    price_base: Decimal
    price_high: Decimal

    actual_price: Optional[Decimal] = None
    is_hit: Optional[bool] = None


# =============================================================================
# PredictionStore - CRUD Operations
# =============================================================================

class PredictionStore:
    """
    Handles CRUD operations for predictions in TimescaleDB.

    Methods:
    - create_prediction: Save new prediction
    - get_latest_prediction: Get most recent prediction for ticker
    - get_prediction_history: Get historical predictions
    - get_corridor_data: Get corridor visualization data
    - get_track_record: Get accuracy statistics
    - get_all_tickers: List all tickers with predictions
    - update_actual_results: Update with actual price (internal)
    """

    def __init__(self, db_url: str):
        """
        Initialize PredictionStore.

        Args:
            db_url: PostgreSQL connection string
        """
        self.db_url = db_url

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.db_url)

    def create_prediction(self, pred: PredictionCreate) -> Prediction:
        """
        Save new prediction to database.

        Args:
            pred: Prediction data to save

        Returns:
            Saved prediction with generated ID
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO predictions (
                        ticker, exchange, horizon_days, target_date,
                        price_at_creation, price_low, price_base, price_high,
                        reasoning, verification_score, model_used, pipeline_cost,
                        was_calibrated, calibration_adj,
                        lower_bound, upper_bound, interval_width, coverage_level, conformal_method
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    RETURNING *
                """, (
                    pred.ticker, pred.exchange, pred.horizon_days, pred.target_date,
                    pred.price_at_creation, pred.price_low, pred.price_base, pred.price_high,
                    Json(pred.reasoning), pred.verification_score, pred.model_used, pred.pipeline_cost,
                    pred.was_calibrated, pred.calibration_adj,
                    pred.lower_bound, pred.upper_bound, pred.interval_width, pred.coverage_level, pred.conformal_method
                ))

                row = cur.fetchone()
                conn.commit()

                logger.info(f"Created prediction {row['id']} for {pred.ticker}")
                return Prediction(**dict(row))

    def get_latest_prediction(self, ticker: str) -> Optional[Prediction]:
        """
        Get most recent prediction for ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Latest prediction or None
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM predictions
                    WHERE ticker = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (ticker,))

                row = cur.fetchone()
                return Prediction(**dict(row)) if row else None

    def get_prediction_history(
        self,
        ticker: str,
        limit: int = 20,
        include_pending: bool = True
    ) -> List[Prediction]:
        """
        Get historical predictions for ticker.

        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of predictions to return
            include_pending: Include predictions without actual results

        Returns:
            List of predictions ordered by created_at DESC
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT * FROM predictions
                    WHERE ticker = %s
                """

                if not include_pending:
                    query += " AND actual_price IS NOT NULL"

                query += " ORDER BY created_at DESC LIMIT %s"

                cur.execute(query, (ticker, limit))

                rows = cur.fetchall()
                return [Prediction(**dict(row)) for row in rows]

    def get_corridor_data(self, ticker: str, limit: int = 10) -> List[CorridorData]:
        """
        Get corridor visualization data for ticker.

        Args:
            ticker: Stock ticker symbol
            limit: Number of recent predictions

        Returns:
            List of corridor data for visualization
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        ticker,
                        created_at as prediction_date,
                        target_date,
                        price_at_creation,
                        price_low,
                        price_base,
                        price_high,
                        actual_price,
                        CASE
                            WHEN actual_price IS NOT NULL THEN
                                actual_price BETWEEN price_low AND price_high
                            ELSE NULL
                        END as is_hit
                    FROM predictions
                    WHERE ticker = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (ticker, limit))

                rows = cur.fetchall()
                return [CorridorData(**dict(row)) for row in rows]

    def get_track_record(self, ticker: Optional[str] = None) -> TrackRecord:
        """
        Get accuracy statistics for predictions.

        Args:
            ticker: Optional ticker to filter by (None for all)

        Returns:
            Track record statistics
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Overall stats
                where_clause = "WHERE ticker = %s" if ticker else ""
                params = (ticker,) if ticker else ()

                cur.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT(actual_price) as completed,
                        COUNT(*) - COUNT(actual_price) as pending,
                        AVG(CASE WHEN accuracy_band = 'HIT' THEN 1.0 ELSE 0.0 END) as hit_rate,
                        AVG(CASE WHEN accuracy_band = 'NEAR' THEN 1.0 ELSE 0.0 END) as near_rate,
                        AVG(CASE WHEN accuracy_band = 'MISS' THEN 1.0 ELSE 0.0 END) as miss_rate,
                        AVG(ABS(error_pct)) as avg_error,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ABS(error_pct)) as median_error
                    FROM predictions
                    {where_clause}
                """, params)

                stats = cur.fetchone()

                # By ticker stats
                cur.execute("""
                    SELECT
                        ticker,
                        COUNT(*) as total,
                        COUNT(actual_price) as completed,
                        AVG(CASE WHEN accuracy_band = 'HIT' THEN 1.0 ELSE 0.0 END) as hit_rate,
                        AVG(ABS(error_pct)) as avg_error
                    FROM predictions
                    GROUP BY ticker
                    ORDER BY total DESC
                """)

                by_ticker = {
                    row['ticker']: {
                        'total': row['total'],
                        'completed': row['completed'],
                        'hit_rate': float(row['hit_rate'] or 0.0),
                        'avg_error': float(row['avg_error'] or 0.0)
                    }
                    for row in cur.fetchall()
                }

                # Recent accuracy (last 10 completed)
                cur.execute(f"""
                    SELECT AVG(CASE WHEN accuracy_band = 'HIT' THEN 1.0 ELSE 0.0 END) as recent_accuracy
                    FROM (
                        SELECT accuracy_band FROM predictions
                        {where_clause}
                        AND actual_price IS NOT NULL
                        ORDER BY created_at DESC
                        LIMIT 10
                    ) recent
                """, params)

                recent = cur.fetchone()

                return TrackRecord(
                    total_predictions=stats['total'],
                    completed_predictions=stats['completed'],
                    pending_predictions=stats['pending'],
                    hit_rate=float(stats['hit_rate'] or 0.0),
                    near_rate=float(stats['near_rate'] or 0.0),
                    miss_rate=float(stats['miss_rate'] or 0.0),
                    avg_error_pct=float(stats['avg_error'] or 0.0),
                    median_error_pct=float(stats['median_error'] or 0.0),
                    by_ticker=by_ticker,
                    recent_accuracy=float(recent['recent_accuracy'] or 0.0)
                )

    def get_all_tickers(self) -> List[str]:
        """
        Get list of all tickers with predictions.

        Returns:
            List of ticker symbols ordered by most recent prediction
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ticker
                    FROM predictions
                    ORDER BY MAX(created_at) DESC
                """)

                return [row[0] for row in cur.fetchall()]

    def update_actual_results(
        self,
        prediction_id: UUID,
        actual_price: Decimal,
        actual_date: date
    ) -> Prediction:
        """
        Update prediction with actual results and calculate accuracy.

        Args:
            prediction_id: Prediction UUID
            actual_price: Actual price at target_date
            actual_date: Date of actual price

        Returns:
            Updated prediction
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Calculate accuracy metrics
                cur.execute("""
                    UPDATE predictions
                    SET
                        actual_price = %s,
                        actual_date = %s,
                        accuracy_band = CASE
                            WHEN %s BETWEEN price_low AND price_high THEN 'HIT'
                            WHEN %s BETWEEN price_low * 0.95 AND price_high * 1.05 THEN 'NEAR'
                            ELSE 'MISS'
                        END,
                        error_pct = ((%s - price_base) / price_base) * 100,
                        error_direction = CASE
                            WHEN %s > price_base THEN 'OVER'
                            WHEN %s < price_base THEN 'UNDER'
                            ELSE 'EXACT'
                        END
                    WHERE id = %s
                    RETURNING *
                """, (
                    actual_price, actual_date,
                    actual_price,  # for accuracy_band BETWEEN check 1
                    actual_price,  # for accuracy_band BETWEEN check 2
                    actual_price,  # for error_pct
                    actual_price,  # for error_direction check 1
                    actual_price,  # for error_direction check 2
                    prediction_id
                ))

                row = cur.fetchone()
                conn.commit()

                if row:
                    logger.info(f"Updated prediction {prediction_id} with actual results")
                    return Prediction(**dict(row))
                else:
                    raise ValueError(f"Prediction {prediction_id} not found")

    def get_pending_predictions(self, days_until_target: int = 7) -> List[Prediction]:
        """
        Get predictions nearing target_date without actual results.

        Args:
            days_until_target: Days before/after target_date to consider

        Returns:
            List of pending predictions
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM predictions
                    WHERE actual_price IS NULL
                    AND target_date BETWEEN
                        CURRENT_DATE - INTERVAL '%s days'
                        AND CURRENT_DATE + INTERVAL '%s days'
                    ORDER BY target_date ASC
                """, (days_until_target, days_until_target))

                rows = cur.fetchall()
                return [Prediction(**dict(row)) for row in rows]
