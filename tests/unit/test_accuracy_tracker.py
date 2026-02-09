"""
Unit tests for AccuracyTracker.

Tests accuracy tracking, price fetching, and band calculation.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4, UUID
import pandas as pd

from src.predictions.accuracy_tracker import AccuracyTracker
from src.predictions.prediction_store import PredictionStore, Prediction


@pytest.fixture
def mock_store():
    """Mock PredictionStore for testing."""
    store = Mock(spec=PredictionStore)
    store._get_connection = MagicMock()
    return store


@pytest.fixture
def tracker(mock_store):
    """AccuracyTracker instance with mocked store."""
    return AccuracyTracker(mock_store)


class TestFetchActualPrice:
    """Tests for fetch_actual_price method."""

    def test_fetch_actual_price_success(self, tracker):
        """Test successful price fetch."""
        with patch('yfinance.Ticker') as mock_ticker:
            # Mock yfinance response
            mock_hist = pd.DataFrame({
                'Close': [150.25]
            }, index=pd.DatetimeIndex([date(2024, 1, 15)]))

            mock_ticker.return_value.history.return_value = mock_hist

            price = tracker.fetch_actual_price('AAPL', date(2024, 1, 15))

            assert price == Decimal('150.25')
            mock_ticker.assert_called_once_with('AAPL')

    def test_fetch_actual_price_no_data(self, tracker):
        """Test price fetch when no data available."""
        with patch('yfinance.Ticker') as mock_ticker:
            # Empty DataFrame
            mock_ticker.return_value.history.return_value = pd.DataFrame()

            price = tracker.fetch_actual_price('INVALID', date(2024, 1, 15))

            assert price is None

    def test_fetch_actual_price_nearest_date(self, tracker):
        """Test price fetch uses nearest date if exact date not available."""
        with patch('yfinance.Ticker') as mock_ticker:
            # Weekend data missing, use Friday
            mock_hist = pd.DataFrame({
                'Close': [150.00, 151.00]
            }, index=pd.DatetimeIndex([date(2024, 1, 12), date(2024, 1, 16)]))

            mock_ticker.return_value.history.return_value = mock_hist

            # Request Saturday (2024-01-13), should get Friday (2024-01-12)
            price = tracker.fetch_actual_price('AAPL', date(2024, 1, 13))

            assert price == Decimal('150.00')

    def test_fetch_actual_price_exception(self, tracker):
        """Test price fetch handles exceptions gracefully."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.history.side_effect = Exception("Network error")

            price = tracker.fetch_actual_price('AAPL', date(2024, 1, 15))

            assert price is None


class TestCalculateBand:
    """Tests for calculate_band method."""

    def test_calculate_band_hit_exact_middle(self, tracker):
        """Test HIT when actual price is exactly in middle of corridor."""
        band = tracker.calculate_band(
            price_low=Decimal('100.00'),
            price_base=Decimal('105.00'),
            price_high=Decimal('110.00'),
            actual_price=Decimal('105.00')
        )
        assert band == 'HIT'

    def test_calculate_band_hit_at_boundary(self, tracker):
        """Test HIT when actual price is at corridor boundary."""
        band = tracker.calculate_band(
            price_low=Decimal('100.00'),
            price_base=Decimal('105.00'),
            price_high=Decimal('110.00'),
            actual_price=Decimal('110.00')
        )
        assert band == 'HIT'

    def test_calculate_band_near_below_corridor(self, tracker):
        """Test NEAR when actual price is below corridor within 5%."""
        # Corridor: 100-110 (width=10)
        # 5% tolerance: 0.5
        # NEAR range below: 99.5-100
        band = tracker.calculate_band(
            price_low=Decimal('100.00'),
            price_base=Decimal('105.00'),
            price_high=Decimal('110.00'),
            actual_price=Decimal('99.75')
        )
        assert band == 'NEAR'

    def test_calculate_band_near_above_corridor(self, tracker):
        """Test NEAR when actual price is above corridor within 5%."""
        # Corridor: 100-110 (width=10)
        # 5% tolerance: 0.5
        # NEAR range above: 110-110.5
        band = tracker.calculate_band(
            price_low=Decimal('100.00'),
            price_base=Decimal('105.00'),
            price_high=Decimal('110.00'),
            actual_price=Decimal('110.25')
        )
        assert band == 'NEAR'

    def test_calculate_band_miss_far_below(self, tracker):
        """Test MISS when actual price is far below corridor."""
        band = tracker.calculate_band(
            price_low=Decimal('100.00'),
            price_base=Decimal('105.00'),
            price_high=Decimal('110.00'),
            actual_price=Decimal('95.00')
        )
        assert band == 'MISS'

    def test_calculate_band_miss_far_above(self, tracker):
        """Test MISS when actual price is far above corridor."""
        band = tracker.calculate_band(
            price_low=Decimal('100.00'),
            price_base=Decimal('105.00'),
            price_high=Decimal('110.00'),
            actual_price=Decimal('115.00')
        )
        assert band == 'MISS'


class TestEvaluatePrediction:
    """Tests for evaluate_prediction method."""

    def test_evaluate_prediction_success(self, tracker, mock_store):
        """Test successful prediction evaluation."""
        pred_id = uuid4()

        # Mock database row matching V002 migration schema
        mock_row = (
            pred_id,  # 0: id
            None,  # 1: created_at
            'AAPL',  # 2: ticker
            'US',  # 3: exchange
            30,  # 4: horizon_days
            date(2024, 1, 15),  # 5: target_date
            Decimal('150.00'),  # 6: price_at_creation
            Decimal('145.00'),  # 7: price_low
            Decimal('150.00'),  # 8: price_base
            Decimal('155.00'),  # 9: price_high
            {},  # 10: reasoning
            0.9,  # 11: verification_score
            'test-model',  # 12: model_used
            Decimal('0.001'),  # 13: pipeline_cost
            None,  # 14: actual_price (not evaluated yet)
            None,  # 15: actual_date
            None,  # 16: accuracy_band
            None,  # 17: error_pct
            None,  # 18: error_direction
            False,  # 19: was_calibrated
            None,  # 20: calibration_adj
        )

        # Mock connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_store._get_connection.return_value = mock_conn

        # Mock fetch_actual_price
        with patch.object(tracker, 'fetch_actual_price', return_value=Decimal('152.00')):
            # Mock update_actual_results
            mock_store.update_actual_results.return_value = Mock()

            result = tracker.evaluate_prediction(pred_id)

            assert result['success'] is True
            assert result['ticker'] == 'AAPL'
            assert result['accuracy_band'] == 'HIT'
            assert result['actual_price'] == Decimal('152.00')
            mock_store.update_actual_results.assert_called_once()

    def test_evaluate_prediction_not_found(self, tracker, mock_store):
        """Test evaluation when prediction not found."""
        pred_id = uuid4()

        # Mock connection returning None
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_store._get_connection.return_value = mock_conn

        result = tracker.evaluate_prediction(pred_id)

        assert result['success'] is False
        assert 'not found' in result['message']

    def test_evaluate_prediction_already_evaluated(self, tracker, mock_store):
        """Test evaluation skips already evaluated predictions."""
        pred_id = uuid4()

        # Mock row with actual_price already set
        mock_row = (
            pred_id,  # 0: id
            None,  # 1: created_at
            'AAPL',  # 2: ticker
            'US',  # 3: exchange
            30,  # 4: horizon_days
            date(2024, 1, 15),  # 5: target_date
            Decimal('150.00'),  # 6: price_at_creation
            Decimal('145.00'),  # 7: price_low
            Decimal('150.00'),  # 8: price_base
            Decimal('155.00'),  # 9: price_high
            {},  # 10: reasoning
            0.9,  # 11: verification_score
            'test-model',  # 12: model_used
            Decimal('0.001'),  # 13: pipeline_cost
            Decimal('152.00'),  # 14: actual_price (already evaluated)
            date(2024, 1, 15),  # 15: actual_date
            'HIT',  # 16: accuracy_band
            1.33,  # 17: error_pct
            'OVER',  # 18: error_direction
            False,  # 19: was_calibrated
            None,  # 20: calibration_adj
        )

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_store._get_connection.return_value = mock_conn

        result = tracker.evaluate_prediction(pred_id)

        assert result['success'] is False
        assert 'already evaluated' in result['message']

    def test_evaluate_prediction_price_fetch_fails(self, tracker, mock_store):
        """Test evaluation when price fetch fails."""
        pred_id = uuid4()

        mock_row = (
            pred_id,  # 0: id
            None,  # 1: created_at
            'AAPL',  # 2: ticker
            'US',  # 3: exchange
            30,  # 4: horizon_days
            date(2024, 1, 15),  # 5: target_date
            Decimal('150.00'),  # 6: price_at_creation
            Decimal('145.00'),  # 7: price_low
            Decimal('150.00'),  # 8: price_base
            Decimal('155.00'),  # 9: price_high
            {},  # 10: reasoning
            0.9,  # 11: verification_score
            'test-model',  # 12: model_used
            Decimal('0.001'),  # 13: pipeline_cost
            None,  # 14: actual_price (not set)
            None,  # 15: actual_date
            None,  # 16: accuracy_band
            None,  # 17: error_pct
            None,  # 18: error_direction
            False,  # 19: was_calibrated
            None,  # 20: calibration_adj
        )

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_store._get_connection.return_value = mock_conn

        # Mock fetch_actual_price returning None
        with patch.object(tracker, 'fetch_actual_price', return_value=None):
            result = tracker.evaluate_prediction(pred_id)

            assert result['success'] is False
            assert 'Could not fetch' in result['message']


class TestRunDailyCheck:
    """Tests for run_daily_check method."""

    def test_run_daily_check_processes_expired_predictions(self, tracker, mock_store):
        """Test daily check processes only expired predictions."""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)

        # Mock pending predictions
        pred_expired = Mock(spec=Prediction)
        pred_expired.id = uuid4()
        pred_expired.target_date = yesterday

        pred_future = Mock(spec=Prediction)
        pred_future.id = uuid4()
        pred_future.target_date = tomorrow

        mock_store.get_pending_predictions.return_value = [pred_expired, pred_future]

        # Mock evaluate_prediction
        with patch.object(tracker, 'evaluate_prediction') as mock_eval:
            mock_eval.return_value = {'success': True}

            results = tracker.run_daily_check(days_until_target=7)

            # Should only evaluate expired prediction
            assert len(results) == 1
            mock_eval.assert_called_once_with(pred_expired.id)

    def test_run_daily_check_empty_pending(self, tracker, mock_store):
        """Test daily check with no pending predictions."""
        mock_store.get_pending_predictions.return_value = []

        results = tracker.run_daily_check()

        assert results == []
