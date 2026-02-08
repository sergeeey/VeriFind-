"""Evaluation and ground truth framework for APE 2026."""

from .synthetic_baseline import SyntheticBaselineGenerator
from .comparison_metrics import ComparisonMetrics

__all__ = ["SyntheticBaselineGenerator", "ComparisonMetrics"]
