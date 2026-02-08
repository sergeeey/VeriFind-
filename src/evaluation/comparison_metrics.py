"""
Comparison Metrics for Ground Truth Validation.

Week 1 Day 4-5: Compare Sonnet predictions with Opus baselines.

Metrics:
1. Directional Agreement: Do they agree on direction (up/down/neutral)?
2. Magnitude Difference: How far apart are numerical predictions?
3. Reasoning Overlap: Semantic similarity of reasoning
4. Confidence Calibration: Is confidence aligned with accuracy?
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re
from difflib import SequenceMatcher


@dataclass
class ComparisonResult:
    """Result of comparing prediction with baseline."""

    # Core agreement
    directional_agreement: Optional[bool]  # True if directions match
    magnitude_difference_pct: Optional[float]  # % difference in magnitude
    reasoning_overlap_score: float  # 0.0-1.0 semantic similarity

    # Confidence analysis
    confidence_diff: float  # baseline.conf - prediction.conf
    is_well_calibrated: bool  # confidence matches agreement

    # Details
    baseline_direction: Optional[str]  # "up", "down", "neutral"
    prediction_direction: Optional[str]
    baseline_magnitude: Optional[float]
    prediction_magnitude: Optional[float]

    # Summary
    overall_agreement_score: float  # 0.0-1.0 composite score


class ComparisonMetrics:
    """
    Metrics for comparing predictions with baselines.

    Purpose:
    1. Shadow mode validation
    2. Model performance tracking
    3. Confidence calibration
    """

    @staticmethod
    def extract_direction(text: str) -> Optional[str]:
        """
        Extract directional signal from text.

        Args:
            text: Prediction or baseline text

        Returns:
            "up", "down", "neutral", or None
        """
        text_lower = text.lower()

        # Bullish indicators
        bullish_terms = [
            'increase', 'rise', 'grow', 'up', 'bullish',
            'higher', 'gain', 'positive', 'upward'
        ]

        # Bearish indicators
        bearish_terms = [
            'decrease', 'fall', 'decline', 'down', 'bearish',
            'lower', 'loss', 'negative', 'downward'
        ]

        bullish_count = sum(1 for term in bullish_terms if term in text_lower)
        bearish_count = sum(1 for term in bearish_terms if term in text_lower)

        if bullish_count > bearish_count:
            return "up"
        elif bearish_count > bullish_count:
            return "down"
        elif bullish_count == bearish_count and bullish_count > 0:
            return "neutral"
        else:
            return None

    @staticmethod
    def extract_magnitude(text: str) -> Optional[float]:
        """
        Extract numerical magnitude from text.

        Args:
            text: Text containing numbers

        Returns:
            First number found, or None
        """
        # Find patterns like: 5%, 2.5, +10%, -3.2%
        pattern = r'[-+]?\d*\.?\d+%?'
        matches = re.findall(pattern, text)

        if matches:
            # Take first number
            num_str = matches[0].replace('%', '').replace('+', '')
            try:
                return float(num_str)
            except ValueError:
                return None

        return None

    @staticmethod
    def calculate_reasoning_overlap(
        baseline_reasoning: str,
        prediction_reasoning: str
    ) -> float:
        """
        Calculate semantic similarity of reasoning.

        Args:
            baseline_reasoning: Baseline reasoning text
            prediction_reasoning: Prediction reasoning text

        Returns:
            Similarity score 0.0-1.0 (SequenceMatcher ratio)
        """
        # Simple word-level similarity (for MVP)
        # TODO: Use sentence embeddings for production
        matcher = SequenceMatcher(
            None,
            baseline_reasoning.lower().split(),
            prediction_reasoning.lower().split()
        )

        return matcher.ratio()

    @staticmethod
    def compare_predictions(
        baseline: Dict[str, Any],
        prediction: Dict[str, Any]
    ) -> ComparisonResult:
        """
        Compare prediction with baseline.

        Args:
            baseline: Baseline prediction dict (from Opus)
            prediction: Model prediction dict (from Sonnet)

        Returns:
            ComparisonResult with all metrics
        """
        # Extract directions
        baseline_dir = ComparisonMetrics.extract_direction(
            baseline.get('prediction', '')
        )
        prediction_dir = ComparisonMetrics.extract_direction(
            prediction.get('prediction', '')
        )

        directional_agreement = None
        if baseline_dir and prediction_dir:
            directional_agreement = (baseline_dir == prediction_dir)

        # Extract magnitudes
        baseline_mag = ComparisonMetrics.extract_magnitude(
            baseline.get('prediction', '')
        )
        prediction_mag = ComparisonMetrics.extract_magnitude(
            prediction.get('prediction', '')
        )

        magnitude_diff_pct = None
        if baseline_mag is not None and prediction_mag is not None:
            if baseline_mag != 0:
                magnitude_diff_pct = abs(
                    (prediction_mag - baseline_mag) / baseline_mag * 100
                )

        # Reasoning overlap
        reasoning_overlap = ComparisonMetrics.calculate_reasoning_overlap(
            baseline.get('reasoning', ''),
            prediction.get('reasoning', '')
        )

        # Confidence analysis
        baseline_conf = baseline.get('confidence', 0.5)
        prediction_conf = prediction.get('confidence', 0.5)
        confidence_diff = baseline_conf - prediction_conf

        # Well-calibrated if:
        # - High confidence (>0.7) + agreement
        # - Low confidence (<0.5) + disagreement
        # - Moderate confidence (0.5-0.7) + small conf diff (<0.2)
        is_well_calibrated = False
        if directional_agreement is not None:
            if directional_agreement and prediction_conf > 0.7:
                # High conf + agreement = calibrated
                is_well_calibrated = True
            elif not directional_agreement and prediction_conf < 0.5:
                # Low conf + disagreement = calibrated
                is_well_calibrated = True
            elif 0.5 <= prediction_conf <= 0.7 and abs(confidence_diff) < 0.2:
                # Moderate conf + similar levels = calibrated
                is_well_calibrated = True
            # High conf + disagreement = NOT calibrated (explicit)

        # Overall agreement score (weighted composite)
        weights = {
            'directional': 0.4,
            'magnitude': 0.3,
            'reasoning': 0.3
        }

        overall_score = 0.0

        if directional_agreement is not None:
            overall_score += weights['directional'] * (
                1.0 if directional_agreement else 0.0
            )

        if magnitude_diff_pct is not None:
            # Invert: closer = higher score
            magnitude_score = max(0, 1.0 - (magnitude_diff_pct / 100))
            overall_score += weights['magnitude'] * magnitude_score

        overall_score += weights['reasoning'] * reasoning_overlap

        return ComparisonResult(
            directional_agreement=directional_agreement,
            magnitude_difference_pct=magnitude_diff_pct,
            reasoning_overlap_score=reasoning_overlap,
            confidence_diff=confidence_diff,
            is_well_calibrated=is_well_calibrated,
            baseline_direction=baseline_dir,
            prediction_direction=prediction_dir,
            baseline_magnitude=baseline_mag,
            prediction_magnitude=prediction_mag,
            overall_agreement_score=overall_score
        )

    @staticmethod
    def aggregate_results(
        results: List[ComparisonResult]
    ) -> Dict[str, float]:
        """
        Aggregate multiple comparison results.

        Args:
            results: List of ComparisonResult objects

        Returns:
            Dictionary with aggregate metrics
        """
        if not results:
            return {}

        total = len(results)

        # Directional agreement rate
        directional_agreements = [
            r for r in results
            if r.directional_agreement is not None
        ]
        directional_agreement_rate = (
            sum(1 for r in directional_agreements if r.directional_agreement)
            / len(directional_agreements)
            if directional_agreements else 0.0
        )

        # Average magnitude difference
        magnitude_diffs = [
            r.magnitude_difference_pct for r in results
            if r.magnitude_difference_pct is not None
        ]
        avg_magnitude_diff = (
            sum(magnitude_diffs) / len(magnitude_diffs)
            if magnitude_diffs else 0.0
        )

        # Average reasoning overlap
        avg_reasoning_overlap = sum(
            r.reasoning_overlap_score for r in results
        ) / total

        # Calibration rate
        calibration_rate = sum(
            1 for r in results if r.is_well_calibrated
        ) / total

        # Average overall agreement
        avg_overall_agreement = sum(
            r.overall_agreement_score for r in results
        ) / total

        return {
            "directional_agreement_rate": directional_agreement_rate,
            "avg_magnitude_difference_pct": avg_magnitude_diff,
            "avg_reasoning_overlap": avg_reasoning_overlap,
            "calibration_rate": calibration_rate,
            "avg_overall_agreement": avg_overall_agreement,
            "sample_size": total
        }
