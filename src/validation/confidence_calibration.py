"""
Confidence Calibration for APE 2026.

Ensures that predicted confidence scores match actual accuracy.
When a model says "80% confident", it should be correct 80% of the time.

Week 9 Day 4: Production Readiness - Confidence Calibration

Key Concepts:
- Temperature Scaling: Simple post-processing that learns optimal temperature T
- ECE (Expected Calibration Error): Measures calibration quality
- Reliability Diagram: Visualizes predicted vs actual accuracy
- Target: ECE < 0.05 (excellent calibration)
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import logging
from scipy.special import expit, logit  # sigmoid and inverse sigmoid
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class CalibrationMethod(str, Enum):
    """Calibration method options."""
    TEMPERATURE_SCALING = "temperature_scaling"
    PLATT_SCALING = "platt_scaling"
    ISOTONIC_REGRESSION = "isotonic_regression"


@dataclass
class ReliabilityDiagram:
    """Data for reliability diagram visualization."""
    bin_centers: List[float]  # Center of each confidence bin
    bin_accuracies: List[float]  # Actual accuracy in each bin
    bin_confidences: List[float]  # Average confidence in each bin
    bin_counts: List[int]  # Number of predictions in each bin
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error


@dataclass
class CalibrationResult:
    """Result of calibration process."""
    method: CalibrationMethod
    temperature: Optional[float] = None
    ece_before: float = 0.0
    ece_after: float = 0.0
    improvement: float = 0.0
    n_samples: int = 0


class ConfidenceCalibrator:
    """
    Calibrates confidence scores to match actual accuracy.

    Design:
    - Temperature scaling: Learns single temperature parameter T
    - Calibrated confidence = sigmoid(logit(original_confidence) / T)
    - T > 1: Lower confidence (overconfident model)
    - T < 1: Raise confidence (underconfident model)
    - T = 1: No change (well-calibrated model)

    Usage:
        calibrator = ConfidenceCalibrator()
        calibrator.fit(confidences, correct_labels)
        calibrated_conf = calibrator.calibrate(0.85)
    """

    def __init__(
        self,
        method: CalibrationMethod = CalibrationMethod.TEMPERATURE_SCALING,
        n_bins: int = 10
    ):
        """
        Initialize confidence calibrator.

        Args:
            method: Calibration method (default: temperature_scaling)
            n_bins: Number of bins for ECE calculation (default: 10)
        """
        self.method = method
        self.n_bins = n_bins
        self.is_fitted = False
        self.temperature: Optional[float] = None

        # For Platt scaling (if implemented)
        self.platt_a: Optional[float] = None
        self.platt_b: Optional[float] = None

    def fit(self, confidences: np.ndarray, correct: np.ndarray) -> CalibrationResult:
        """
        Fit calibration model on validation data.

        Args:
            confidences: Predicted confidence scores (0-1 range)
            correct: Binary labels (1 = correct, 0 = incorrect)

        Returns:
            CalibrationResult with fitted parameters
        """
        confidences = np.asarray(confidences, dtype=np.float64)
        correct = np.asarray(correct, dtype=np.int32)

        if len(confidences) != len(correct):
            raise ValueError("confidences and correct must have same length")

        if len(confidences) < 2:
            logger.warning("Insufficient data for calibration (n=%d). Using default temperature=1.0",
                          len(confidences))
            self.temperature = 1.0
            self.is_fitted = True
            return CalibrationResult(
                method=self.method,
                temperature=1.0,
                n_samples=len(confidences)
            )

        # Calculate ECE before calibration
        ece_before = self.calculate_ece(confidences, correct, self.n_bins)

        # Fit temperature scaling
        if self.method == CalibrationMethod.TEMPERATURE_SCALING:
            self.temperature = self._fit_temperature_scaling(confidences, correct)
        else:
            raise NotImplementedError(f"Method {self.method} not implemented yet")

        self.is_fitted = True

        # Calculate ECE after calibration
        calibrated = self.calibrate_batch(confidences)
        ece_after = self.calculate_ece(calibrated, correct, self.n_bins)

        improvement = ece_before - ece_after

        logger.info(
            "Calibration complete: T=%.3f, ECE before=%.4f, ECE after=%.4f, improvement=%.4f",
            self.temperature, ece_before, ece_after, improvement
        )

        return CalibrationResult(
            method=self.method,
            temperature=self.temperature,
            ece_before=ece_before,
            ece_after=ece_after,
            improvement=improvement,
            n_samples=len(confidences)
        )

    def _fit_temperature_scaling(self, confidences: np.ndarray, correct: np.ndarray) -> float:
        """
        Fit temperature parameter using NLL (Negative Log-Likelihood) minimization.

        Args:
            confidences: Predicted confidence scores
            correct: Binary correctness labels

        Returns:
            Optimal temperature parameter T
        """
        # Convert confidences to logits
        # Add small epsilon to avoid log(0) and log(1)
        eps = 1e-7
        confidences_clipped = np.clip(confidences, eps, 1 - eps)
        logits = np.log(confidences_clipped / (1 - confidences_clipped))

        def nll_loss(T):
            """Negative log-likelihood loss for given temperature."""
            T = T[0]  # Scalar
            if T <= 0:
                return 1e10  # Penalize non-positive temperatures

            # Scale logits by temperature
            scaled_logits = logits / T

            # Convert back to probabilities
            scaled_probs = expit(scaled_logits)

            # Binary cross-entropy loss
            scaled_probs_clipped = np.clip(scaled_probs, eps, 1 - eps)
            loss = -np.mean(
                correct * np.log(scaled_probs_clipped) +
                (1 - correct) * np.log(1 - scaled_probs_clipped)
            )
            return loss

        # Optimize temperature (start from T=1.0)
        result = minimize(nll_loss, x0=[1.0], method='Nelder-Mead', options={'maxiter': 1000})

        optimal_T = result.x[0]

        # Constrain temperature to reasonable range [0.1, 10]
        optimal_T = np.clip(optimal_T, 0.1, 10.0)

        return float(optimal_T)

    def calibrate(self, confidence: float) -> float:
        """
        Calibrate a single confidence score.

        Args:
            confidence: Original confidence score (0-1)

        Returns:
            Calibrated confidence score (0-1)

        Raises:
            ValueError: If calibrator not fitted
        """
        if not self.is_fitted:
            raise ValueError("Calibrator not fitted. Call fit() first.")

        if self.method == CalibrationMethod.TEMPERATURE_SCALING:
            return self._calibrate_temperature_scaling(confidence)
        else:
            raise NotImplementedError(f"Method {self.method} not implemented yet")

    def calibrate_batch(self, confidences: np.ndarray) -> np.ndarray:
        """
        Calibrate multiple confidence scores at once.

        Args:
            confidences: Array of confidence scores (0-1)

        Returns:
            Array of calibrated confidence scores (0-1)
        """
        if not self.is_fitted:
            raise ValueError("Calibrator not fitted. Call fit() first.")

        confidences = np.asarray(confidences, dtype=np.float64)

        if self.method == CalibrationMethod.TEMPERATURE_SCALING:
            return np.array([self._calibrate_temperature_scaling(c) for c in confidences])
        else:
            raise NotImplementedError(f"Method {self.method} not implemented yet")

    def _calibrate_temperature_scaling(self, confidence: float) -> float:
        """
        Apply temperature scaling to a confidence score.

        Formula: calibrated = sigmoid(logit(confidence) / T)

        Args:
            confidence: Original confidence (0-1)

        Returns:
            Calibrated confidence (0-1)
        """
        # Handle edge cases
        eps = 1e-7
        confidence = np.clip(confidence, eps, 1 - eps)

        # Convert to logit
        logit_conf = np.log(confidence / (1 - confidence))

        # Scale by temperature
        scaled_logit = logit_conf / self.temperature

        # Convert back to probability
        calibrated = expit(scaled_logit)

        return float(np.clip(calibrated, 0.0, 1.0))

    def calculate_ece(
        self,
        confidences: np.ndarray,
        correct: np.ndarray,
        n_bins: Optional[int] = None
    ) -> float:
        """
        Calculate Expected Calibration Error (ECE).

        ECE measures the difference between predicted confidence and actual accuracy.
        Lower ECE = better calibration. Target: ECE < 0.05

        Formula:
            ECE = Σ (n_b / n) * |accuracy_b - confidence_b|
            where b = bin, n_b = samples in bin, n = total samples

        Args:
            confidences: Predicted confidence scores (0-1)
            correct: Binary correctness labels (0 or 1)
            n_bins: Number of bins (default: use self.n_bins)

        Returns:
            ECE value (0-1 range, lower is better)
        """
        if n_bins is None:
            n_bins = self.n_bins

        confidences = np.asarray(confidences, dtype=np.float64)
        correct = np.asarray(correct, dtype=np.int32)

        # Create bins
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(confidences, bin_edges[:-1]) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        ece = 0.0
        total_samples = len(confidences)

        for bin_idx in range(n_bins):
            # Get samples in this bin
            in_bin = bin_indices == bin_idx
            n_in_bin = np.sum(in_bin)

            if n_in_bin == 0:
                continue

            # Average confidence in bin
            bin_confidence = np.mean(confidences[in_bin])

            # Actual accuracy in bin
            bin_accuracy = np.mean(correct[in_bin])

            # Weighted difference
            ece += (n_in_bin / total_samples) * abs(bin_accuracy - bin_confidence)

        return float(ece)

    def generate_reliability_diagram(
        self,
        confidences: np.ndarray,
        correct: np.ndarray,
        n_bins: Optional[int] = None
    ) -> ReliabilityDiagram:
        """
        Generate data for reliability diagram visualization.

        A reliability diagram plots predicted confidence vs actual accuracy.
        Perfect calibration = diagonal line.

        Args:
            confidences: Predicted confidence scores
            correct: Binary correctness labels
            n_bins: Number of bins (default: use self.n_bins)

        Returns:
            ReliabilityDiagram with bin data
        """
        if n_bins is None:
            n_bins = self.n_bins

        confidences = np.asarray(confidences, dtype=np.float64)
        correct = np.asarray(correct, dtype=np.int32)

        # Create bins
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_indices = np.digitize(confidences, bin_edges[:-1]) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        bin_accuracies = []
        bin_confidences = []
        bin_counts = []

        for bin_idx in range(n_bins):
            in_bin = bin_indices == bin_idx
            n_in_bin = np.sum(in_bin)

            if n_in_bin == 0:
                # Empty bin
                bin_accuracies.append(np.nan)
                bin_confidences.append(np.nan)
                bin_counts.append(0)
            else:
                bin_accuracies.append(float(np.mean(correct[in_bin])))
                bin_confidences.append(float(np.mean(confidences[in_bin])))
                bin_counts.append(int(n_in_bin))

        # Calculate ECE and MCE (Maximum Calibration Error)
        ece = self.calculate_ece(confidences, correct, n_bins)

        # MCE = max bin error
        mce = 0.0
        for acc, conf in zip(bin_accuracies, bin_confidences):
            if not np.isnan(acc) and not np.isnan(conf):
                mce = max(mce, abs(acc - conf))

        return ReliabilityDiagram(
            bin_centers=bin_centers.tolist(),
            bin_accuracies=bin_accuracies,
            bin_confidences=bin_confidences,
            bin_counts=bin_counts,
            ece=ece,
            mce=float(mce)
        )

    def to_dict(self) -> Dict:
        """
        Serialize calibrator to dictionary.

        Returns:
            Dictionary with calibrator parameters
        """
        return {
            'method': self.method.value,
            'n_bins': self.n_bins,
            'is_fitted': self.is_fitted,
            'temperature': self.temperature,
            'platt_a': self.platt_a,
            'platt_b': self.platt_b
        }

    def from_dict(self, data: Dict):
        """
        Load calibrator from dictionary.

        Args:
            data: Dictionary with calibrator parameters
        """
        self.method = CalibrationMethod(data['method'])
        self.n_bins = data['n_bins']
        self.is_fitted = data['is_fitted']
        self.temperature = data['temperature']
        self.platt_a = data.get('platt_a')
        self.platt_b = data.get('platt_b')
