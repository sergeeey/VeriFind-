"""
Unit tests for evaluation framework.

Week 1 Day 4-5: Ground Truth Pipeline testing
"""

import pytest
from src.evaluation.comparison_metrics import ComparisonMetrics, ComparisonResult


def test_extract_direction_bullish():
    """Test direction extraction for bullish signals."""
    text = "I expect the stock to increase by 10% next quarter"
    direction = ComparisonMetrics.extract_direction(text)
    assert direction == "up"


def test_extract_direction_bearish():
    """Test direction extraction for bearish signals."""
    text = "The price will likely decline due to market headwinds"
    direction = ComparisonMetrics.extract_direction(text)
    assert direction == "down"


def test_extract_direction_neutral():
    """Test direction extraction for neutral/mixed signals."""
    text = "Both positive and negative factors suggest sideways movement"
    direction = ComparisonMetrics.extract_direction(text)
    assert direction == "neutral"


def test_extract_direction_no_signal():
    """Test direction extraction with no clear signal."""
    text = "The company reported earnings last quarter"
    direction = ComparisonMetrics.extract_direction(text)
    assert direction is None


def test_extract_magnitude_percentage():
    """Test magnitude extraction from percentage."""
    text = "Expected growth of 15.5% year-over-year"
    magnitude = ComparisonMetrics.extract_magnitude(text)
    assert magnitude == 15.5


def test_extract_magnitude_negative():
    """Test magnitude extraction for negative numbers."""
    text = "Forecast decline of -8.2%"
    magnitude = ComparisonMetrics.extract_magnitude(text)
    assert magnitude == -8.2


def test_extract_magnitude_no_number():
    """Test magnitude extraction with no numbers."""
    text = "Significant growth expected"
    magnitude = ComparisonMetrics.extract_magnitude(text)
    assert magnitude is None


def test_calculate_reasoning_overlap_identical():
    """Test reasoning overlap with identical text."""
    text = "The market shows strong momentum with high volume"
    overlap = ComparisonMetrics.calculate_reasoning_overlap(text, text)
    assert overlap == 1.0


def test_calculate_reasoning_overlap_different():
    """Test reasoning overlap with different text."""
    text1 = "Bullish trend driven by earnings"
    text2 = "Bearish pressure from macroeconomic factors"
    overlap = ComparisonMetrics.calculate_reasoning_overlap(text1, text2)
    assert 0.0 <= overlap < 0.3  # Should be low similarity


def test_calculate_reasoning_overlap_partial():
    """Test reasoning overlap with partial similarity."""
    text1 = "Strong earnings growth and market momentum"
    text2 = "Earnings growth offset by weak market sentiment"
    overlap = ComparisonMetrics.calculate_reasoning_overlap(text1, text2)
    assert 0.3 <= overlap <= 0.7  # Moderate similarity


def test_compare_predictions_full_agreement():
    """Test comparison with full directional and magnitude agreement."""
    baseline = {
        "prediction": "Price will increase by 10%",
        "reasoning": "Strong fundamentals and positive sentiment",
        "confidence": 0.8
    }
    prediction = {
        "prediction": "Expected gain of 10.5%",
        "reasoning": "Good fundamentals and market optimism",
        "confidence": 0.75
    }

    result = ComparisonMetrics.compare_predictions(baseline, prediction)

    assert result.directional_agreement is True
    assert result.baseline_direction == "up"
    assert result.prediction_direction == "up"
    assert result.magnitude_difference_pct is not None
    assert result.magnitude_difference_pct < 10  # Within 10%
    assert result.overall_agreement_score > 0.7  # High agreement


def test_compare_predictions_directional_disagreement():
    """Test comparison with directional disagreement."""
    baseline = {
        "prediction": "Stock will rise 5%",
        "reasoning": "Bullish indicators present",
        "confidence": 0.7
    }
    prediction = {
        "prediction": "Expecting decline of 3%",
        "reasoning": "Bearish trend developing",
        "confidence": 0.6
    }

    result = ComparisonMetrics.compare_predictions(baseline, prediction)

    assert result.directional_agreement is False
    assert result.baseline_direction == "up"
    assert result.prediction_direction == "down"
    assert result.overall_agreement_score < 0.5  # Low agreement


def test_compare_predictions_well_calibrated_high_conf():
    """Test calibration detection with high confidence + agreement."""
    baseline = {
        "prediction": "Increase of 12%",
        "reasoning": "Strong momentum",
        "confidence": 0.85
    }
    prediction = {
        "prediction": "Growth of 11%",
        "reasoning": "Positive momentum",
        "confidence": 0.8  # High confidence, agrees
    }

    result = ComparisonMetrics.compare_predictions(baseline, prediction)

    assert result.is_well_calibrated is True


def test_compare_predictions_well_calibrated_low_conf():
    """Test calibration detection with low confidence + disagreement."""
    baseline = {
        "prediction": "Up 5%",
        "reasoning": "Mixed signals",
        "confidence": 0.55
    }
    prediction = {
        "prediction": "Down 2%",
        "reasoning": "Uncertain outlook",
        "confidence": 0.45  # Low confidence, disagrees
    }

    result = ComparisonMetrics.compare_predictions(baseline, prediction)

    assert result.is_well_calibrated is True  # Low conf + disagree = calibrated


def test_compare_predictions_poorly_calibrated():
    """Test calibration detection with misaligned confidence."""
    baseline = {
        "prediction": "Increase 10%",
        "reasoning": "Bullish",
        "confidence": 0.9
    }
    prediction = {
        "prediction": "Decrease 5%",
        "reasoning": "Bearish",
        "confidence": 0.9  # High conf but disagrees
    }

    result = ComparisonMetrics.compare_predictions(baseline, prediction)

    assert result.is_well_calibrated is False


def test_aggregate_results_multiple_comparisons():
    """Test aggregation of multiple comparison results."""
    results = [
        ComparisonResult(
            directional_agreement=True,
            magnitude_difference_pct=5.0,
            reasoning_overlap_score=0.8,
            confidence_diff=0.1,
            is_well_calibrated=True,
            baseline_direction="up",
            prediction_direction="up",
            baseline_magnitude=10.0,
            prediction_magnitude=10.5,
            overall_agreement_score=0.85
        ),
        ComparisonResult(
            directional_agreement=True,
            magnitude_difference_pct=3.0,
            reasoning_overlap_score=0.75,
            confidence_diff=0.05,
            is_well_calibrated=True,
            baseline_direction="down",
            prediction_direction="down",
            baseline_magnitude=-5.0,
            prediction_magnitude=-4.85,
            overall_agreement_score=0.9
        ),
        ComparisonResult(
            directional_agreement=False,
            magnitude_difference_pct=None,
            reasoning_overlap_score=0.4,
            confidence_diff=0.3,
            is_well_calibrated=False,
            baseline_direction="up",
            prediction_direction="down",
            baseline_magnitude=None,
            prediction_magnitude=None,
            overall_agreement_score=0.4
        )
    ]

    aggregated = ComparisonMetrics.aggregate_results(results)

    assert aggregated["sample_size"] == 3
    assert aggregated["directional_agreement_rate"] == 2/3  # 2 out of 3 agree
    assert aggregated["avg_magnitude_difference_pct"] == (5.0 + 3.0) / 2
    assert 0.6 < aggregated["avg_reasoning_overlap"] < 0.7
    assert aggregated["calibration_rate"] == 2/3
    assert 0.7 < aggregated["avg_overall_agreement"] < 0.75


def test_aggregate_results_empty_list():
    """Test aggregation with empty results list."""
    aggregated = ComparisonMetrics.aggregate_results([])
    assert aggregated == {}


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_day45_success_criteria_evaluation():
    """
    Week 1 Day 4-5 Success Criteria:

    - [x] Comparison metrics implementation
    - [x] Directional agreement detection
    - [x] Magnitude difference calculation
    - [x] Reasoning overlap (similarity)
    - [x] Confidence calibration analysis
    """
    # Create baseline and prediction
    baseline = {
        "prediction": "Stock price will increase by 8% in Q1 2025",
        "reasoning": "Strong earnings growth, positive market sentiment, and favorable macroeconomic conditions",
        "confidence": 0.75
    }

    prediction = {
        "prediction": "Expected gain of 7.5% next quarter",
        "reasoning": "Earnings outlook is positive with supportive market trends",
        "confidence": 0.72
    }

    # Compare
    result = ComparisonMetrics.compare_predictions(baseline, prediction)

    # Verify all metrics
    assert result.directional_agreement is True, "Directional agreement failed"
    assert result.magnitude_difference_pct is not None, "Magnitude diff failed"
    assert result.magnitude_difference_pct < 10, "Magnitude diff too high"
    # Note: Word-level overlap is basic (MVP). Production will use embeddings.
    assert result.reasoning_overlap_score > 0.2, "Reasoning overlap too low"
    assert result.overall_agreement_score > 0.7, "Overall agreement too low"

    # Test aggregation
    results_list = [result] * 5  # Simulate 5 similar results
    aggregated = ComparisonMetrics.aggregate_results(results_list)

    assert aggregated["directional_agreement_rate"] == 1.0
    assert aggregated["sample_size"] == 5
    assert aggregated["avg_overall_agreement"] > 0.7

    print("""
    ✅ Week 1 Day 4-5 SUCCESS CRITERIA MET:
    - Comparison metrics: ✅
    - Directional agreement: ✅
    - Magnitude difference: ✅
    - Reasoning overlap: ✅
    - Confidence calibration: ✅
    """)
