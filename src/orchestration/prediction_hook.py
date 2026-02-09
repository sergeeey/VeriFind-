"""
Pipeline → Predictions integration hook.

Automatically saves completed pipeline results as predictions in TimescaleDB.
Week 9 Day 3 - Prediction Dashboard Backend
"""

import re
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from src.orchestration.langgraph_orchestrator import APEState, StateStatus
from src.predictions.prediction_store import PredictionStore, PredictionCreate

logger = logging.getLogger(__name__)


def extract_ticker(query_text: str) -> Optional[str]:
    """
    Extract ticker symbol from query text.

    Looks for common patterns:
    - "AAPL stock price"
    - "What is TSLA trading at"
    - "SPY 50-day moving average"
    - Ticker must be 1-5 uppercase letters

    Args:
        query_text: User query string

    Returns:
        Ticker symbol (uppercase) or None if not found
    """
    # Pattern: 1-5 uppercase letters that likely represent a ticker
    # Look for word boundaries to avoid false matches
    patterns = [
        r'\b([A-Z]{1,5})\b',  # AAPL, SPY, TSLA
        r'ticker[:\s]+([A-Z]{1,5})',  # ticker: AAPL
        r'symbol[:\s]+([A-Z]{1,5})',  # symbol: AAPL
    ]

    for pattern in patterns:
        match = re.search(pattern, query_text)
        if match:
            ticker = match.group(1)
            # Filter out common false positives (abbreviations, not tickers)
            if ticker not in ['API', 'USD', 'EUR', 'GBP', 'JPY', 'MA', 'RSI', 'MACD']:
                return ticker

    return None


def extract_price_prediction(extracted_values: Dict[str, Any]) -> Optional[Dict[str, Decimal]]:
    """
    Extract price prediction from verified fact extracted values.

    Looks for patterns:
    - 'predicted_price', 'price_prediction', 'target_price'
    - 'price_low', 'price_high', 'price_base'
    - 'price', 'current_price' (for baseline)

    Args:
        extracted_values: Dictionary of numerical values from VEE execution

    Returns:
        Dict with keys: price_at_creation, price_low, price_base, price_high
        or None if insufficient data
    """
    if not extracted_values:
        return None

    # Try to find prediction values
    price_base = None
    price_low = None
    price_high = None
    price_current = None

    # Look for explicit prediction keys
    for key, value in extracted_values.items():
        key_lower = key.lower()

        if 'predicted_price' in key_lower or 'target_price' in key_lower or 'price_base' in key_lower:
            price_base = Decimal(str(value))
        elif 'price_low' in key_lower or 'lower_bound' in key_lower:
            price_low = Decimal(str(value))
        elif 'price_high' in key_lower or 'upper_bound' in key_lower:
            price_high = Decimal(str(value))
        elif 'current_price' in key_lower or key_lower == 'price':
            price_current = Decimal(str(value))

    # If we have base prediction but not bounds, create corridor (±10%)
    if price_base and not (price_low and price_high):
        price_low = price_base * Decimal('0.9')
        price_high = price_base * Decimal('1.1')

    # If we have bounds but no base, calculate middle
    if (price_low and price_high) and not price_base:
        price_base = (price_low + price_high) / Decimal('2')

    # Use current price as baseline if available
    if not price_current and price_base:
        price_current = price_base

    # Validate we have minimum required data
    if price_base and price_low and price_high and price_current:
        return {
            'price_at_creation': price_current,
            'price_low': price_low,
            'price_base': price_base,
            'price_high': price_high,
        }

    return None


def save_prediction_from_result(
    state: APEState,
    store: PredictionStore,
    default_horizon_days: int = 30
) -> Optional[str]:
    """
    Extract prediction data from completed APEState and save to TimescaleDB.

    Returns prediction_id if saved successfully, None if not applicable.

    Does NOT save if:
    - status != 'completed'
    - No ticker found in query
    - No numerical prediction in verified_fact
    - verified_fact is None or has no extracted_values

    Args:
        state: Completed APEState from pipeline
        store: PredictionStore instance
        default_horizon_days: Default prediction horizon if not specified (default: 30)

    Returns:
        Prediction UUID as string if saved, None otherwise
    """
    # Validation 1: Status must be COMPLETED
    if state.status != StateStatus.COMPLETED:
        logger.debug(f"Query {state.query_id}: status is {state.status}, not COMPLETED. Skipping prediction save.")
        return None

    # Validation 2: Must have verified_fact
    if not state.verified_fact:
        logger.debug(f"Query {state.query_id}: no verified_fact. Skipping prediction save.")
        return None

    # Validation 3: verified_fact must have extracted_values
    if not state.verified_fact.extracted_values:
        logger.debug(f"Query {state.query_id}: verified_fact has no extracted_values. Skipping prediction save.")
        return None

    # Extract ticker from query
    ticker = extract_ticker(state.query_text)
    if not ticker:
        logger.debug(f"Query {state.query_id}: no ticker found in query '{state.query_text}'. Skipping prediction save.")
        return None

    # Extract price prediction
    price_data = extract_price_prediction(state.verified_fact.extracted_values)
    if not price_data:
        logger.debug(f"Query {state.query_id}: no price prediction found in extracted_values. Skipping prediction save.")
        return None

    try:
        # Build reasoning from synthesis (if available)
        reasoning = {
            'summary': state.synthesis.verdict if state.synthesis else 'Prediction from pipeline execution',
            'key_factors': [],
        }

        # Add debate insights if available
        if state.debate_reports:
            reasoning['key_factors'] = [
                report.verdict for report in state.debate_reports if hasattr(report, 'verdict')
            ][:3]  # Top 3 perspectives

        # If no key factors, add placeholder
        if not reasoning['key_factors']:
            reasoning['key_factors'] = ['Automated pipeline prediction']

        # Calculate target date
        target_date = date.today() + timedelta(days=default_horizon_days)

        # Create prediction
        prediction_create = PredictionCreate(
            ticker=ticker,
            exchange='US',
            horizon_days=default_horizon_days,
            target_date=target_date,
            price_at_creation=price_data['price_at_creation'],
            price_low=price_data['price_low'],
            price_base=price_data['price_base'],
            price_high=price_data['price_high'],
            reasoning=reasoning,
            verification_score=state.verified_fact.confidence_score,
            model_used='APE-Pipeline-v1',
            pipeline_cost=Decimal('0.001'),  # Placeholder, would track actual cost
            was_calibrated=False,
        )

        # Save to database
        prediction = store.create_prediction(prediction_create)

        logger.info(
            f"Query {state.query_id}: saved prediction {prediction.id} for {ticker} "
            f"(target: {target_date}, base: ${price_data['price_base']})"
        )

        return str(prediction.id)

    except Exception as e:
        logger.error(f"Query {state.query_id}: failed to save prediction: {e}", exc_info=True)
        return None
