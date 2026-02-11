"""
Prediction calibration analytics for APE 2026.

Computes calibration curve, Expected Calibration Error (ECE), Brier score,
and recommendation hints based on evaluated predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional


@dataclass
class CalibrationPoint:
    """Single prediction point used for calibration analytics."""

    confidence: float
    outcome: float  # 1.0 for correct, 0.0 for incorrect


class CalibrationTracker:
    """Calibration metrics calculator for prediction outcomes."""

    def __init__(self, prediction_store):
        self.store = prediction_store

    @staticmethod
    def _clip_confidence(value: Any) -> float:
        confidence = float(value)
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _outcome_from_band(accuracy_band: Optional[str]) -> float:
        # Keep binary target for ECE/Brier.
        return 1.0 if str(accuracy_band or "").upper() == "HIT" else 0.0

    def get_evaluated_points(self, days: int = 30, ticker: Optional[str] = None) -> List[CalibrationPoint]:
        """
        Load evaluated predictions (actual result available) for calibration period.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        where = "actual_price IS NOT NULL AND created_at >= %s"
        params: List[Any] = [cutoff]
        if ticker:
            where += " AND ticker = %s"
            params.append(str(ticker).upper())

        with self.store._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT verification_score, accuracy_band
                    FROM predictions
                    WHERE {where}
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        points: List[CalibrationPoint] = []
        for row in rows:
            # Handle tuple row format (default cursor) and mapping format.
            if isinstance(row, dict):
                confidence = row.get("verification_score", 0.0)
                accuracy_band = row.get("accuracy_band")
            else:
                confidence = row[0]
                accuracy_band = row[1]
            points.append(
                CalibrationPoint(
                    confidence=self._clip_confidence(confidence),
                    outcome=self._outcome_from_band(accuracy_band),
                )
            )
        return points

    def compute_calibration_curve(self, points: List[CalibrationPoint], bins: int = 10) -> List[Dict[str, Any]]:
        """Compute calibration bins with predicted probability vs actual accuracy."""
        if bins <= 0:
            raise ValueError("bins must be positive")

        bin_size = 1.0 / bins
        curve: List[Dict[str, Any]] = []

        for idx in range(bins):
            lower = idx * bin_size
            upper = lower + bin_size
            if idx == bins - 1:
                in_bin = [p for p in points if lower <= p.confidence <= upper]
            else:
                in_bin = [p for p in points if lower <= p.confidence < upper]

            if in_bin:
                predicted_prob = sum(p.confidence for p in in_bin) / len(in_bin)
                actual_accuracy = sum(p.outcome for p in in_bin) / len(in_bin)
            else:
                predicted_prob = round(lower + (bin_size / 2), 4)
                actual_accuracy = 0.0

            curve.append(
                {
                    "confidence_bin": f"{lower:.1f}-{upper:.1f}",
                    "predicted_prob": round(float(predicted_prob), 4),
                    "actual_accuracy": round(float(actual_accuracy), 4),
                    "count": len(in_bin),
                }
            )

        return curve

    def compute_expected_calibration_error(self, points: List[CalibrationPoint], bins: int = 10) -> float:
        """Compute Expected Calibration Error (ECE). Lower is better."""
        if not points:
            return 0.0

        curve = self.compute_calibration_curve(points=points, bins=bins)
        total = len(points)
        ece = 0.0
        for row in curve:
            if row["count"] == 0:
                continue
            weight = row["count"] / total
            ece += weight * abs(row["actual_accuracy"] - row["predicted_prob"])
        return round(float(ece), 6)

    def compute_brier_score(self, points: List[CalibrationPoint]) -> float:
        """Compute Brier score. Lower is better."""
        if not points:
            return 0.0

        error = sum((p.confidence - p.outcome) ** 2 for p in points) / len(points)
        return round(float(error), 6)

    def recommend_adjustments(
        self,
        calibration_curve: List[Dict[str, Any]],
        min_count: int = 5,
        threshold: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """Generate confidence adjustment recommendations by bin."""
        recommendations: List[Dict[str, Any]] = []

        for row in calibration_curve:
            if row["count"] < min_count:
                continue

            gap = row["actual_accuracy"] - row["predicted_prob"]
            if abs(gap) < threshold:
                continue

            issue = "underconfident" if gap > 0 else "overconfident"
            adjustment = round(gap, 4)
            recommendations.append(
                {
                    "bin": row["confidence_bin"],
                    "issue": issue,
                    "adjustment": adjustment,
                    "message": (
                        f"Model is {issue} in {row['confidence_bin']} "
                        f"by {abs(adjustment) * 100:.1f}%"
                    ),
                }
            )

        return recommendations

    def calculate_summary(
        self,
        days: int = 30,
        ticker: Optional[str] = None,
        bins: int = 10,
        min_samples: int = 10,
    ) -> Dict[str, Any]:
        """Compute complete calibration summary payload for API/scheduler."""
        points = self.get_evaluated_points(days=days, ticker=ticker)
        if len(points) < min_samples:
            return {
                "calibration_period": f"{days} days",
                "total_evaluated": len(points),
                "expected_calibration_error": 0.0,
                "brier_score": 0.0,
                "calibration_curve": [],
                "recommendations": [],
                "status": "insufficient_data",
                "min_required_samples": min_samples,
            }

        curve = self.compute_calibration_curve(points=points, bins=bins)
        ece = self.compute_expected_calibration_error(points=points, bins=bins)
        brier = self.compute_brier_score(points=points)
        recommendations = self.recommend_adjustments(calibration_curve=curve)

        return {
            "calibration_period": f"{days} days",
            "total_evaluated": len(points),
            "expected_calibration_error": ece,
            "brier_score": brier,
            "calibration_curve": curve,
            "recommendations": recommendations,
            "status": "ok",
            "min_required_samples": min_samples,
        }

