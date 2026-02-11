"""
Conformal Prediction for APE 2026.

Week 13 Day 1: Uncertainty quantification via Conformal Prediction.

Provides prediction intervals with guaranteed coverage for financial predictions.

Features:
- Asymmetric intervals (larger downside risk)
- Volatility adjustment
- Adaptive intervals based on market conditions
- Coverage evaluation

References:
- Vovk et al. (2005) "Algorithmic Learning in a Random World"
- Shafer & Vovk (2008) "A Tutorial on Conformal Prediction"
- Romano et al. (2019) "Conformalized Quantile Regression"

Usage:
    from src.predictions.conformal import FinancialConformalPredictor

    predictor = FinancialConformalPredictor(
        coverage_level=0.95,
        method='asymmetric'
    )

    # Fit on calibration data
    predictor.fit(calibration_residuals, calibration_features)

    # Predict with intervals
    prediction, lower, upper = predictor.predict(
        point_estimate=250.0,
        features={'volatility': 0.25, 'trend': 'up'}
    )
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class ConformalMethod(str, Enum):
    """Conformal prediction methods."""
    NAIVE = "naive"  # Simple symmetric intervals
    NAIVE_ASYMMETRIC = "naive_asymmetric"  # Asymmetric intervals (larger downside)
    QUANTILE = "quantile"  # Quantile-based intervals
    CQR = "cqr"  # Conformalized Quantile Regression
    ADAPTIVE = "adaptive"  # Adaptive intervals based on features


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ConformalInterval:
    """
    Prediction interval from Conformal Prediction.

    Attributes:
        point_estimate: Point prediction (e.g., $250)
        lower_bound: Lower bound of interval (e.g., $235)
        upper_bound: Upper bound of interval (e.g., $265)
        coverage_level: Target coverage probability (e.g., 0.95)
        width: Interval width (upper - lower)
        method: Conformal method used
    """
    point_estimate: float
    lower_bound: float
    upper_bound: float
    coverage_level: float
    width: float
    method: ConformalMethod

    def __post_init__(self):
        """Validate interval."""
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                f"Lower bound ({self.lower_bound}) > upper bound ({self.upper_bound})"
            )
        if not (0.0 < self.coverage_level < 1.0):
            raise ValueError(
                f"Coverage level must be in (0, 1), got {self.coverage_level}"
            )

    @property
    def contains_estimate(self) -> bool:
        """Check if interval contains point estimate."""
        return self.lower_bound <= self.point_estimate <= self.upper_bound

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            'point_estimate': self.point_estimate,
            'lower_bound': self.lower_bound,
            'upper_bound': self.upper_bound,
            'coverage_level': self.coverage_level,
            'width': self.width,
            'method': self.method.value,
            'contains_estimate': self.contains_estimate
        }


# ============================================================================
# Base Conformal Predictor
# ============================================================================

class ConformalPredictor:
    """
    Base class for Conformal Prediction.

    Implements split conformal prediction with guaranteed coverage.
    """

    def __init__(
        self,
        coverage_level: float = 0.95,
        method: ConformalMethod = ConformalMethod.NAIVE
    ):
        """
        Initialize Conformal Predictor.

        Args:
            coverage_level: Target coverage probability (default: 0.95)
            method: Conformal method to use
        """
        if not (0.0 < coverage_level < 1.0):
            raise ValueError(f"Coverage level must be in (0, 1), got {coverage_level}")

        self.coverage_level = coverage_level
        self.method = method
        self.calibration_scores: Optional[np.ndarray] = None
        self.quantile: Optional[float] = None
        self.is_fitted = False

        logger.info(
            f"Initialized ConformalPredictor (coverage={coverage_level}, "
            f"method={method.value})"
        )

    def fit(
        self,
        calibration_residuals: List[float],
        calibration_features: Optional[Dict[str, List[float]]] = None
    ) -> None:
        """
        Fit conformal predictor on calibration data.

        Args:
            calibration_residuals: Residuals from calibration set (actual - predicted)
            calibration_features: Optional features for adaptive methods
        """
        if len(calibration_residuals) == 0:
            raise ValueError("Calibration residuals cannot be empty")

        self.calibration_scores = np.abs(calibration_residuals)

        # Compute quantile for interval width
        # Use (n+1) * (1 - alpha) / n for finite-sample validity
        n = len(calibration_residuals)
        adjusted_level = (n + 1) * self.coverage_level / n
        adjusted_level = min(adjusted_level, 1.0)  # Clip to 1.0

        self.quantile = np.quantile(self.calibration_scores, adjusted_level)
        self.is_fitted = True

        logger.info(
            f"Fitted ConformalPredictor on {n} calibration points. "
            f"Quantile={self.quantile:.4f}"
        )

    def predict(
        self,
        point_estimate: float,
        features: Optional[Dict[str, Any]] = None
    ) -> ConformalInterval:
        """
        Predict with conformal interval.

        Args:
            point_estimate: Point prediction from model
            features: Optional features for adaptive methods

        Returns:
            ConformalInterval with bounds
        """
        if not self.is_fitted:
            raise RuntimeError("Predictor not fitted. Call fit() first.")

        # Compute interval based on method
        if self.method == ConformalMethod.NAIVE:
            lower, upper = self._predict_naive(point_estimate)
        elif self.method == ConformalMethod.NAIVE_ASYMMETRIC:
            lower, upper = self._predict_naive_asymmetric(point_estimate, features)
        elif self.method == ConformalMethod.ADAPTIVE:
            lower, upper = self._predict_adaptive(point_estimate, features)
        else:
            raise NotImplementedError(f"Method {self.method} not implemented")

        width = upper - lower

        return ConformalInterval(
            point_estimate=point_estimate,
            lower_bound=lower,
            upper_bound=upper,
            coverage_level=self.coverage_level,
            width=width,
            method=self.method
        )

    def _predict_naive(self, point_estimate: float) -> Tuple[float, float]:
        """Naive symmetric intervals."""
        lower = point_estimate - self.quantile
        upper = point_estimate + self.quantile
        return lower, upper

    def _predict_naive_asymmetric(
        self,
        point_estimate: float,
        features: Optional[Dict[str, Any]]
    ) -> Tuple[float, float]:
        """
        Asymmetric intervals (larger downside).

        Financial markets have asymmetric risk:
        - Downside losses can be larger than upside gains
        - Use 60/40 split (60% downside, 40% upside)
        """
        # Asymmetric split: 60% downside, 40% upside
        downside_factor = 0.60
        upside_factor = 0.40

        lower = point_estimate - (self.quantile * downside_factor / 0.5)
        upper = point_estimate + (self.quantile * upside_factor / 0.5)

        return lower, upper

    def _predict_adaptive(
        self,
        point_estimate: float,
        features: Optional[Dict[str, Any]]
    ) -> Tuple[float, float]:
        """
        Adaptive intervals based on features.

        Adjusts interval width based on:
        - Volatility (wider intervals for high volatility)
        - Trend strength (wider for weak trends)
        - Market conditions
        """
        if features is None:
            # Fallback to naive if no features
            return self._predict_naive(point_estimate)

        # Get volatility (default: 0.0)
        volatility = features.get('volatility', 0.0)

        # Adjust quantile based on volatility
        # Higher volatility → wider intervals
        volatility_factor = 1.0 + volatility
        adjusted_quantile = self.quantile * volatility_factor

        lower = point_estimate - adjusted_quantile
        upper = point_estimate + adjusted_quantile

        return lower, upper

    def evaluate_coverage(
        self,
        test_predictions: List[float],
        test_actuals: List[float],
        test_features: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, float]:
        """
        Evaluate coverage on test set.

        Args:
            test_predictions: Point predictions
            test_actuals: Actual outcomes
            test_features: Optional features per prediction

        Returns:
            Dict with coverage metrics
        """
        if not self.is_fitted:
            raise RuntimeError("Predictor not fitted. Call fit() first.")

        if len(test_predictions) != len(test_actuals):
            raise ValueError("Predictions and actuals must have same length")

        n = len(test_predictions)
        covered = 0
        widths = []

        for i, (pred, actual) in enumerate(zip(test_predictions, test_actuals)):
            features = test_features[i] if test_features else None
            interval = self.predict(pred, features)

            if interval.lower_bound <= actual <= interval.upper_bound:
                covered += 1

            widths.append(interval.width)

        coverage = covered / n
        avg_width = np.mean(widths)

        return {
            'coverage': coverage,
            'target_coverage': self.coverage_level,
            'coverage_gap': abs(coverage - self.coverage_level),
            'avg_width': avg_width,
            'n_test': n,
            'n_covered': covered
        }


# ============================================================================
# Financial Conformal Predictor
# ============================================================================

class FinancialConformalPredictor(ConformalPredictor):
    """
    Conformal Predictor specialized for financial predictions.

    Features:
    - Asymmetric intervals (larger downside)
    - Volatility adjustment
    - Market regime awareness
    """

    def __init__(
        self,
        coverage_level: float = 0.95,
        method: ConformalMethod = ConformalMethod.NAIVE_ASYMMETRIC,
        volatility_adjustment: bool = True
    ):
        """
        Initialize Financial Conformal Predictor.

        Args:
            coverage_level: Target coverage (default: 0.95)
            method: Conformal method (default: naive_asymmetric)
            volatility_adjustment: Whether to adjust for volatility
        """
        super().__init__(coverage_level, method)
        self.volatility_adjustment = volatility_adjustment

    def predict(
        self,
        point_estimate: float,
        features: Optional[Dict[str, Any]] = None
    ) -> ConformalInterval:
        """
        Predict with financial-aware conformal interval.

        Applies volatility adjustment if enabled.
        """
        if not self.is_fitted:
            raise RuntimeError("Predictor not fitted. Call fit() first.")

        # Apply volatility adjustment if enabled
        if self.volatility_adjustment and features and 'volatility' in features:
            volatility = features['volatility']

            # High volatility → wider intervals
            if volatility > 0.3:  # High volatility threshold
                # Increase quantile by 20%
                original_quantile = self.quantile
                self.quantile *= 1.2

                interval = super().predict(point_estimate, features)

                # Restore original quantile
                self.quantile = original_quantile

                return interval

        return super().predict(point_estimate, features)
