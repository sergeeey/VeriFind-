"""
Unit tests for prediction_hook.py

Tests pipeline → predictions integration.
"""

import pytest
from datetime import date, datetime, timedelta, UTC
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, MagicMock

from src.orchestration.prediction_hook import (
    extract_ticker,
    extract_price_prediction,
    save_prediction_from_result,
)
from src.orchestration.langgraph_orchestrator import APEState, StateStatus
from src.truth_boundary.gate import VerifiedFact
from src.predictions.prediction_store import PredictionStore, Prediction


class TestExtractTicker:
    """Tests for extract_ticker function."""

    def test_extract_ticker_simple(self):
        """Test extracting simple ticker."""
        assert extract_ticker("What is AAPL stock price?") == "AAPL"
        assert extract_ticker("Calculate TSLA 50-day MA") == "TSLA"
        assert extract_ticker("SPY analysis") == "SPY"

    def test_extract_ticker_with_context(self):
        """Test extracting ticker with surrounding context."""
        assert extract_ticker("ticker: NVDA latest price") == "NVDA"
        assert extract_ticker("symbol: MSFT performance") == "MSFT"

    def test_extract_ticker_no_match(self):
        """Test when no ticker found."""
        assert extract_ticker("What is the market doing?") is None
        assert extract_ticker("Calculate moving average") is None
        assert extract_ticker("price analysis") is None

    def test_extract_ticker_filters_false_positives(self):
        """Test filtering out abbreviations that aren't tickers."""
        # These should be filtered out
        assert extract_ticker("Use the API to fetch data") is None
        assert extract_ticker("Price in USD") is None
        assert extract_ticker("50-day MA calculation") is None

    def test_extract_ticker_case_sensitive(self):
        """Test that only uppercase tickers are matched."""
        assert extract_ticker("AAPL is great") == "AAPL"
        # Lowercase should not match
        assert extract_ticker("aapl is great") is None


class TestExtractPricePrediction:
    """Tests for extract_price_prediction function."""

    def test_extract_price_explicit_values(self):
        """Test extracting explicit price prediction values."""
        extracted_values = {
            'current_price': 150.0,
            'predicted_price': 160.0,
            'price_low': 155.0,
            'price_high': 165.0,
        }

        result = extract_price_prediction(extracted_values)

        assert result is not None
        assert result['price_at_creation'] == Decimal('150.0')
        assert result['price_base'] == Decimal('160.0')
        assert result['price_low'] == Decimal('155.0')
        assert result['price_high'] == Decimal('165.0')

    def test_extract_price_with_corridor_calculation(self):
        """Test creating corridor when only base price provided."""
        extracted_values = {
            'price': 100.0,
            'target_price': 110.0,
        }

        result = extract_price_prediction(extracted_values)

        assert result is not None
        assert result['price_base'] == Decimal('110.0')
        # Corridor should be ±10%
        assert result['price_low'] == Decimal('110.0') * Decimal('0.9')
        assert result['price_high'] == Decimal('110.0') * Decimal('1.1')

    def test_extract_price_from_bounds_only(self):
        """Test calculating base price from bounds."""
        extracted_values = {
            'current_price': 100.0,
            'lower_bound': 95.0,
            'upper_bound': 105.0,
        }

        result = extract_price_prediction(extracted_values)

        assert result is not None
        # Base should be middle of bounds
        assert result['price_base'] == Decimal('100.0')
        assert result['price_low'] == Decimal('95.0')
        assert result['price_high'] == Decimal('105.0')

    def test_extract_price_no_data(self):
        """Test when no price data available."""
        assert extract_price_prediction({}) is None
        assert extract_price_prediction({'volume': 1000000}) is None
        assert extract_price_prediction(None) is None

    def test_extract_price_partial_data(self):
        """Test when only partial price data available."""
        # Only base price, should create corridor and use base as current
        result = extract_price_prediction({'predicted_price': 150.0})
        assert result is not None  # Uses predicted_price as current_price
        assert result['price_base'] == Decimal('150.0')
        assert result['price_at_creation'] == Decimal('150.0')

        # With explicit current price
        result = extract_price_prediction({
            'price': 140.0,
            'predicted_price': 150.0
        })
        assert result is not None
        assert result['price_base'] == Decimal('150.0')
        assert result['price_at_creation'] == Decimal('140.0')


class TestSavePredictionFromResult:
    """Tests for save_prediction_from_result function."""

    @pytest.fixture
    def mock_store(self):
        """Mock PredictionStore."""
        store = Mock(spec=PredictionStore)
        mock_prediction = Mock(spec=Prediction)
        mock_prediction.id = uuid4()
        store.create_prediction.return_value = mock_prediction
        return store

    @pytest.fixture
    def completed_state(self):
        """Create completed APEState with prediction data."""
        state = APEState.from_query(
            query_id=str(uuid4()),
            query_text="What is AAPL predicted price for next month?"
        )
        state.status = StateStatus.COMPLETED
        state.verified_fact = VerifiedFact(
            fact_id=str(uuid4()),
            query_id=state.query_id,
            plan_id=str(uuid4()),
            code_hash="abc123",
            status="success",
            extracted_values={
                'current_price': 150.0,
                'predicted_price': 160.0,
                'price_low': 155.0,
                'price_high': 165.0,
            },
            execution_time_ms=100,
            memory_used_mb=10.0,
            created_at=datetime.now(UTC),
            confidence_score=0.85,
        )
        return state

    def test_save_prediction_success(self, completed_state, mock_store):
        """Test successful prediction save."""
        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is not None
        assert mock_store.create_prediction.called

        # Verify call arguments
        call_args = mock_store.create_prediction.call_args[0][0]
        assert call_args.ticker == 'AAPL'
        assert call_args.price_base == Decimal('160.0')
        assert call_args.verification_score == 0.85

    def test_save_prediction_status_not_completed(self, completed_state, mock_store):
        """Test skipping when status is not COMPLETED."""
        completed_state.status = StateStatus.PLANNING

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is None
        assert not mock_store.create_prediction.called

    def test_save_prediction_no_verified_fact(self, completed_state, mock_store):
        """Test skipping when no verified_fact."""
        completed_state.verified_fact = None

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is None
        assert not mock_store.create_prediction.called

    def test_save_prediction_no_extracted_values(self, completed_state, mock_store):
        """Test skipping when verified_fact has no extracted_values."""
        completed_state.verified_fact.extracted_values = {}

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is None
        assert not mock_store.create_prediction.called

    def test_save_prediction_no_ticker(self, completed_state, mock_store):
        """Test skipping when no ticker found in query."""
        completed_state.query_text = "Calculate some financial metric"

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is None
        assert not mock_store.create_prediction.called

    def test_save_prediction_no_price_data(self, completed_state, mock_store):
        """Test skipping when no price prediction in extracted_values."""
        completed_state.verified_fact.extracted_values = {
            'volume': 1000000,
            'volatility': 0.25,
        }

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is None
        assert not mock_store.create_prediction.called

    def test_save_prediction_with_synthesis(self, completed_state, mock_store):
        """Test prediction save includes synthesis data."""
        # Add synthesis
        completed_state.synthesis = Mock()
        completed_state.synthesis.verdict = "Price likely to increase based on technical analysis"

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is not None

        # Verify reasoning includes synthesis
        call_args = mock_store.create_prediction.call_args[0][0]
        assert 'technical analysis' in call_args.reasoning['summary']

    def test_save_prediction_with_debate_reports(self, completed_state, mock_store):
        """Test prediction save includes debate insights."""
        # Add debate reports
        report1 = Mock()
        report1.verdict = "Bullish outlook"
        report2 = Mock()
        report2.verdict = "Strong fundamentals"

        completed_state.debate_reports = [report1, report2]

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        assert prediction_id is not None

        # Verify reasoning includes debate insights
        call_args = mock_store.create_prediction.call_args[0][0]
        assert 'Bullish outlook' in call_args.reasoning['key_factors']
        assert 'Strong fundamentals' in call_args.reasoning['key_factors']

    def test_save_prediction_error_handling(self, completed_state, mock_store):
        """Test error handling when save fails."""
        mock_store.create_prediction.side_effect = Exception("Database error")

        prediction_id = save_prediction_from_result(completed_state, mock_store)

        # Should return None instead of raising
        assert prediction_id is None
