"""
Unit tests for Conformal Prediction.

Week 13 Day 1: Test conformal prediction with synthetic data.
"""

import pytest
import numpy as np
from src.predictions.conformal import (
    ConformalPredictor,
    FinancialConformalPredictor,
    ConformalInterval,
    ConformalMethod
)


class TestConformalInterval:
    """Test ConformalInterval dataclass."""

    def test_valid_interval(self):
        """Test creating valid interval."""
        interval = ConformalInterval(
            point_estimate=100.0,
            lower_bound=90.0,
            upper_bound=110.0,
            coverage_level=0.95,
            width=20.0,
            method=ConformalMethod.NAIVE
        )

        assert interval.point_estimate == 100.0
        assert interval.lower_bound == 90.0
        assert interval.upper_bound == 110.0
        assert interval.width == 20.0
        assert interval.contains_estimate is True

    def test_invalid_interval(self):
        """Test that invalid intervals raise errors."""
        with pytest.raises(ValueError, match="Lower bound.*upper bound"):
            ConformalInterval(
                point_estimate=100.0,
                lower_bound=110.0,  # Invalid: lower > upper
                upper_bound=90.0,
                coverage_level=0.95,
                width=20.0,
                method=ConformalMethod.NAIVE
            )

    def test_invalid_coverage(self):
        """Test that invalid coverage levels raise errors."""
        with pytest.raises(ValueError, match="Coverage level"):
            ConformalInterval(
                point_estimate=100.0,
                lower_bound=90.0,
                upper_bound=110.0,
                coverage_level=1.5,  # Invalid: > 1.0
                width=20.0,
                method=ConformalMethod.NAIVE
            )

    def test_contains_estimate(self):
        """Test contains_estimate property."""
        # Estimate inside interval
        interval1 = ConformalInterval(
            point_estimate=100.0,
            lower_bound=90.0,
            upper_bound=110.0,
            coverage_level=0.95,
            width=20.0,
            method=ConformalMethod.NAIVE
        )
        assert interval1.contains_estimate is True

        # Estimate outside interval
        interval2 = ConformalInterval(
            point_estimate=100.0,
            lower_bound=110.0,
            upper_bound=120.0,
            coverage_level=0.95,
            width=10.0,
            method=ConformalMethod.NAIVE
        )
        assert interval2.contains_estimate is False

    def test_to_dict(self):
        """Test serialization to dict."""
        interval = ConformalInterval(
            point_estimate=100.0,
            lower_bound=90.0,
            upper_bound=110.0,
            coverage_level=0.95,
            width=20.0,
            method=ConformalMethod.NAIVE
        )

        data = interval.to_dict()

        assert data['point_estimate'] == 100.0
        assert data['lower_bound'] == 90.0
        assert data['upper_bound'] == 110.0
        assert data['coverage_level'] == 0.95
        assert data['width'] == 20.0
        assert data['method'] == 'naive'
        assert data['contains_estimate'] is True


class TestConformalPredictor:
    """Test ConformalPredictor base class."""

    def test_initialization(self):
        """Test predictor initialization."""
        predictor = ConformalPredictor(
            coverage_level=0.90,
            method=ConformalMethod.NAIVE
        )

        assert predictor.coverage_level == 0.90
        assert predictor.method == ConformalMethod.NAIVE
        assert predictor.is_fitted is False

    def test_invalid_coverage(self):
        """Test that invalid coverage raises error."""
        with pytest.raises(ValueError, match="Coverage level"):
            ConformalPredictor(coverage_level=1.5)

    def test_fit(self):
        """Test fitting on calibration data."""
        predictor = ConformalPredictor()

        # Generate synthetic residuals
        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()

        predictor.fit(calibration_residuals)

        assert predictor.is_fitted is True
        assert predictor.quantile is not None
        assert predictor.quantile > 0

    def test_fit_empty_data(self):
        """Test that fitting on empty data raises error."""
        predictor = ConformalPredictor()

        with pytest.raises(ValueError, match="cannot be empty"):
            predictor.fit([])

    def test_predict_before_fit(self):
        """Test that predicting before fit raises error."""
        predictor = ConformalPredictor()

        with pytest.raises(RuntimeError, match="not fitted"):
            predictor.predict(100.0)

    def test_predict_naive(self):
        """Test naive symmetric prediction."""
        predictor = ConformalPredictor(
            coverage_level=0.95,
            method=ConformalMethod.NAIVE
        )

        # Fit on calibration data
        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()
        predictor.fit(calibration_residuals)

        # Predict
        interval = predictor.predict(point_estimate=100.0)

        assert isinstance(interval, ConformalInterval)
        assert interval.point_estimate == 100.0
        assert interval.lower_bound < 100.0
        assert interval.upper_bound > 100.0
        assert interval.coverage_level == 0.95
        assert interval.method == ConformalMethod.NAIVE

        # Check symmetry (naive method)
        downside = 100.0 - interval.lower_bound
        upside = interval.upper_bound - 100.0
        assert abs(downside - upside) < 0.01  # Approximately symmetric

    def test_predict_naive_asymmetric(self):
        """Test asymmetric prediction (larger downside)."""
        predictor = ConformalPredictor(
            coverage_level=0.95,
            method=ConformalMethod.NAIVE_ASYMMETRIC
        )

        # Fit
        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()
        predictor.fit(calibration_residuals)

        # Predict
        interval = predictor.predict(point_estimate=100.0)

        # Check asymmetry (60/40 split)
        downside = 100.0 - interval.lower_bound
        upside = interval.upper_bound - 100.0

        # Downside should be larger
        assert downside > upside

        # Approximate 60/40 ratio
        ratio = downside / upside
        assert 1.3 < ratio < 1.7  # Should be ~1.5 (60/40)

    def test_predict_adaptive(self):
        """Test adaptive prediction with volatility."""
        predictor = ConformalPredictor(
            coverage_level=0.95,
            method=ConformalMethod.ADAPTIVE
        )

        # Fit
        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()
        predictor.fit(calibration_residuals)

        # Predict with low volatility
        interval_low = predictor.predict(
            point_estimate=100.0,
            features={'volatility': 0.1}
        )

        # Predict with high volatility
        interval_high = predictor.predict(
            point_estimate=100.0,
            features={'volatility': 0.5}
        )

        # High volatility should have wider intervals
        assert interval_high.width > interval_low.width

    def test_evaluate_coverage(self):
        """Test coverage evaluation on test set."""
        predictor = ConformalPredictor()

        # Fit on calibration data
        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()
        predictor.fit(calibration_residuals)

        # Generate test data
        test_predictions = [100.0] * 50
        test_actuals = np.random.normal(100, 10, size=50).tolist()

        # Evaluate
        metrics = predictor.evaluate_coverage(test_predictions, test_actuals)

        assert 'coverage' in metrics
        assert 'target_coverage' in metrics
        assert 'coverage_gap' in metrics
        assert 'avg_width' in metrics
        assert metrics['n_test'] == 50

        # Coverage should be close to target (0.95)
        # With 50 samples, expect some variance
        assert 0.7 < metrics['coverage'] < 1.0

    def test_evaluate_coverage_mismatched_lengths(self):
        """Test that mismatched lengths raise error."""
        predictor = ConformalPredictor()

        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()
        predictor.fit(calibration_residuals)

        with pytest.raises(ValueError, match="same length"):
            predictor.evaluate_coverage(
                test_predictions=[100.0, 110.0],
                test_actuals=[100.0]  # Mismatched length
            )


class TestFinancialConformalPredictor:
    """Test FinancialConformalPredictor."""

    def test_initialization(self):
        """Test financial predictor initialization."""
        predictor = FinancialConformalPredictor(
            coverage_level=0.95,
            method=ConformalMethod.NAIVE_ASYMMETRIC,
            volatility_adjustment=True
        )

        assert predictor.coverage_level == 0.95
        assert predictor.method == ConformalMethod.NAIVE_ASYMMETRIC
        assert predictor.volatility_adjustment is True

    def test_volatility_adjustment(self):
        """Test that high volatility widens intervals."""
        predictor = FinancialConformalPredictor(
            volatility_adjustment=True
        )

        # Fit
        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()
        predictor.fit(calibration_residuals)

        # Predict with low volatility
        interval_low = predictor.predict(
            point_estimate=100.0,
            features={'volatility': 0.1}
        )

        # Predict with high volatility (> 0.3)
        interval_high = predictor.predict(
            point_estimate=100.0,
            features={'volatility': 0.4}
        )

        # High volatility should have wider intervals (20% increase)
        assert interval_high.width > interval_low.width

    def test_no_volatility_adjustment(self):
        """Test prediction without volatility adjustment."""
        predictor = FinancialConformalPredictor(
            volatility_adjustment=False
        )

        # Fit
        np.random.seed(42)
        calibration_residuals = np.random.normal(0, 10, size=100).tolist()
        predictor.fit(calibration_residuals)

        # Predict with high volatility (should not affect interval)
        interval1 = predictor.predict(
            point_estimate=100.0,
            features={'volatility': 0.1}
        )

        interval2 = predictor.predict(
            point_estimate=100.0,
            features={'volatility': 0.9}
        )

        # Intervals should be same width (no adjustment)
        assert abs(interval1.width - interval2.width) < 0.01


class TestIntegration:
    """Integration tests for conformal prediction workflow."""

    def test_full_workflow(self):
        """Test complete workflow: fit → predict → evaluate."""
        # 1. Create predictor
        predictor = FinancialConformalPredictor(
            coverage_level=0.95,
            method=ConformalMethod.NAIVE_ASYMMETRIC
        )

        # 2. Generate synthetic calibration data
        np.random.seed(42)
        n_cal = 100
        calibration_predictions = np.random.uniform(90, 110, size=n_cal)
        calibration_actuals = calibration_predictions + np.random.normal(0, 5, size=n_cal)
        calibration_residuals = (calibration_actuals - calibration_predictions).tolist()

        # 3. Fit predictor
        predictor.fit(calibration_residuals)
        assert predictor.is_fitted is True

        # 4. Make predictions with intervals
        test_prediction = 100.0
        interval = predictor.predict(
            point_estimate=test_prediction,
            features={'volatility': 0.2}
        )

        assert isinstance(interval, ConformalInterval)
        assert interval.lower_bound < test_prediction < interval.upper_bound

        # 5. Evaluate coverage on test set
        n_test = 50
        test_predictions = np.random.uniform(90, 110, size=n_test).tolist()
        test_actuals = (
            np.array(test_predictions) + np.random.normal(0, 5, size=n_test)
        ).tolist()

        metrics = predictor.evaluate_coverage(test_predictions, test_actuals)

        assert metrics['n_test'] == n_test
        assert 0.7 < metrics['coverage'] < 1.0  # Should be close to 0.95
        assert metrics['avg_width'] > 0
