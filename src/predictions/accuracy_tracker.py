"""
Accuracy Tracker for APE 2026.

Automatically compares predictions with actual prices and updates accuracy metrics.
Week 9 Day 3 - Prediction Dashboard Backend
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

import yfinance as yf

from .prediction_store import PredictionStore, Prediction

logger = logging.getLogger(__name__)


class AccuracyTracker:
    """
    Tracks prediction accuracy by fetching actual prices and comparing with predictions.

    Methods:
    - fetch_actual_price: Get real price via yfinance on target_date
    - calculate_band: Determine HIT/NEAR/MISS accuracy band
    - evaluate_prediction: Compare prediction with actual, update DB
    - run_daily_check: Check all pending predictions with expired target_date
    """

    def __init__(self, prediction_store: PredictionStore):
        """
        Initialize AccuracyTracker.

        Args:
            prediction_store: PredictionStore instance for database operations
        """
        self.store = prediction_store

    def fetch_actual_price(self, ticker: str, target_date: date) -> Optional[Decimal]:
        """
        Get actual closing price for ticker on target_date via yfinance.

        Args:
            ticker: Stock ticker symbol
            target_date: Target date for price

        Returns:
            Closing price as Decimal, or None if not available
        """
        try:
            # Fetch data with 5-day buffer to handle weekends/holidays
            start_date = target_date - timedelta(days=5)
            end_date = target_date + timedelta(days=1)

            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                logger.warning(f"No price data for {ticker} around {target_date}")
                return None

            # Find closest date to target_date
            hist.index = hist.index.date
            if target_date in hist.index:
                close_price = hist.loc[target_date, 'Close']
            else:
                # Get nearest date
                closest_date = min(hist.index, key=lambda d: abs((d - target_date).days))
                close_price = hist.loc[closest_date, 'Close']
                logger.info(f"Using {closest_date} price for {ticker} (target: {target_date})")

            return Decimal(str(round(close_price, 4)))

        except Exception as e:
            logger.error(f"Failed to fetch price for {ticker} on {target_date}: {e}")
            return None

    def calculate_band(
        self,
        price_low: Decimal,
        price_base: Decimal,
        price_high: Decimal,
        actual_price: Decimal
    ) -> str:
        """
        Determine accuracy band: HIT/NEAR/MISS.

        Rules:
        - HIT: actual_price within [price_low, price_high]
        - NEAR: actual_price deviates from corridor by less than 5%
        - MISS: everything else

        Args:
            price_low: Lower bound of prediction corridor
            price_base: Base prediction price
            price_high: Upper bound of prediction corridor
            actual_price: Actual price observed

        Returns:
            'HIT', 'NEAR', or 'MISS'
        """
        # HIT: inside corridor
        if price_low <= actual_price <= price_high:
            return 'HIT'

        # NEAR: within 5% of corridor bounds
        corridor_width = price_high - price_low
        tolerance = corridor_width * Decimal('0.05')

        if price_low - tolerance <= actual_price < price_low:
            return 'NEAR'  # Below corridor but within 5%
        if price_high < actual_price <= price_high + tolerance:
            return 'NEAR'  # Above corridor but within 5%

        # MISS: outside corridor by more than 5%
        return 'MISS'

    def evaluate_prediction(self, prediction_id: UUID) -> Dict[str, Any]:
        """
        Evaluate a single prediction by comparing with actual price.

        Args:
            prediction_id: UUID of prediction to evaluate

        Returns:
            Evaluation result dictionary with keys:
            - success: bool
            - prediction_id: UUID
            - ticker: str
            - target_date: date
            - actual_price: Decimal or None
            - accuracy_band: str or None
            - error_pct: float or None
            - message: str
        """
        # Get prediction from database
        # Note: We need to add get_prediction_by_id to PredictionStore
        # For now, we'll work around this limitation
        try:
            # Fetch prediction (using internal method access)
            with self.store._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM predictions WHERE id = %s",
                        (prediction_id,)
                    )
                    row = cur.fetchone()

            if not row:
                return {
                    'success': False,
                    'prediction_id': prediction_id,
                    'message': f"Prediction {prediction_id} not found"
                }

            # Parse row into Prediction (manual since we don't have RealDictCursor here)
            # Column order from V002_create_predictions.py migration:
            # 0:id, 1:created_at, 2:ticker, 3:exchange, 4:horizon_days, 5:target_date,
            # 6:price_at_creation, 7:price_low, 8:price_base, 9:price_high,
            # 10:reasoning, 11:verification_score, 12:model_used, 13:pipeline_cost,
            # 14:actual_price, 15:actual_date, 16:accuracy_band, 17:error_pct,
            # 18:error_direction, 19:was_calibrated, 20:calibration_adj
            ticker = row[2]
            target_date = row[5]
            price_low = row[7]
            price_base = row[8]
            price_high = row[9]

            # Check if already evaluated
            actual_price_existing = row[14]  # actual_price column
            if actual_price_existing is not None:
                return {
                    'success': False,
                    'prediction_id': prediction_id,
                    'ticker': ticker,
                    'target_date': target_date,
                    'message': f"Prediction {prediction_id} already evaluated"
                }

            # Fetch actual price
            actual_price = self.fetch_actual_price(ticker, target_date)

            if actual_price is None:
                return {
                    'success': False,
                    'prediction_id': prediction_id,
                    'ticker': ticker,
                    'target_date': target_date,
                    'message': f"Could not fetch actual price for {ticker} on {target_date}"
                }

            # Calculate accuracy band
            accuracy_band = self.calculate_band(price_low, price_base, price_high, actual_price)

            # Calculate error percentage
            error_pct = float((actual_price - price_base) / price_base * 100)

            # Determine error direction
            if actual_price > price_base:
                error_direction = 'OVER'
            elif actual_price < price_base:
                error_direction = 'UNDER'
            else:
                error_direction = 'EXACT'

            # Update database
            updated = self.store.update_actual_results(
                prediction_id=prediction_id,
                actual_price=actual_price,
                actual_date=target_date
            )

            logger.info(
                f"Evaluated prediction {prediction_id}: {ticker} on {target_date}, "
                f"band={accuracy_band}, error={error_pct:.2f}%"
            )

            return {
                'success': True,
                'prediction_id': prediction_id,
                'ticker': ticker,
                'target_date': target_date,
                'actual_price': actual_price,
                'accuracy_band': accuracy_band,
                'error_pct': error_pct,
                'error_direction': error_direction,
                'message': f"Prediction evaluated successfully: {accuracy_band}"
            }

        except Exception as e:
            logger.error(f"Failed to evaluate prediction {prediction_id}: {e}")
            return {
                'success': False,
                'prediction_id': prediction_id,
                'message': f"Evaluation failed: {str(e)}"
            }

    def run_daily_check(self, days_until_target: int = 7) -> List[Dict[str, Any]]:
        """
        Check all pending predictions with expired target_date.

        Args:
            days_until_target: Days before/after target_date to consider (default: 7)

        Returns:
            List of evaluation results for each processed prediction
        """
        logger.info(f"Starting daily accuracy check (days_until_target={days_until_target})")

        # Get pending predictions
        pending = self.store.get_pending_predictions(days_until_target=days_until_target)

        results = []
        for prediction in pending:
            # Only evaluate if target_date has passed
            if prediction.target_date > date.today():
                logger.debug(f"Skipping prediction {prediction.id} (target_date in future)")
                continue

            result = self.evaluate_prediction(prediction.id)
            results.append(result)

        successful = sum(1 for r in results if r['success'])
        logger.info(
            f"Daily check complete: {successful}/{len(results)} predictions evaluated successfully"
        )

        return results
