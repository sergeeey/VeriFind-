"""
Unit tests for Domain Constraints Validator.

Week 9 Day 3: Domain validation - ensuring queries are financial in nature.

Tests validate that:
1. Financial queries are accepted
2. Non-financial queries are rejected
3. Edge cases are handled with confidence penalties
4. Clear error messages are provided
"""

import pytest
from src.validation.domain_constraints import (
    DomainConstraintsValidator,
    DomainValidationResult,
    DomainCategory
)


class TestDomainConstraintsValidator:
    """Tests for DomainConstraintsValidator class."""

    def setup_method(self):
        """Setup test instance."""
        self.validator = DomainConstraintsValidator()

    # ========================================================================
    # Financial Queries - Should Pass
    # ========================================================================

    def test_validate_stock_query(self):
        """Test that stock-related query is accepted."""
        query = "Calculate the Sharpe ratio for AAPL from 2023-01-01 to 2023-12-31"

        result = self.validator.validate(query)

        assert result.is_valid is True
        assert result.domain_category == DomainCategory.FINANCIAL
        assert result.confidence_score > 0.8
        assert result.rejection_reason is None

    def test_validate_portfolio_query(self):
        """Test that portfolio query is accepted."""
        query = "What is the correlation between SPY and QQQ in my portfolio?"

        result = self.validator.validate(query)

        assert result.is_valid is True
        assert result.domain_category == DomainCategory.FINANCIAL
        assert result.confidence_score >= 0.8

    def test_validate_financial_metric_query(self):
        """Test that financial metric query is accepted."""
        query = "Calculate the volatility of TSLA over the last quarter"

        result = self.validator.validate(query)

        assert result.is_valid is True
        assert result.domain_category == DomainCategory.FINANCIAL

    def test_validate_market_analysis_query(self):
        """Test that market analysis query is accepted."""
        query = "Analyze the beta of GOOGL relative to the S&P 500 index"

        result = self.validator.validate(query)

        assert result.is_valid is True
        assert result.domain_category == DomainCategory.FINANCIAL

    def test_validate_trading_query(self):
        """Test that trading-related query is accepted."""
        query = "What are the moving averages for MSFT stock?"

        result = self.validator.validate(query)

        assert result.is_valid is True
        assert result.domain_category == DomainCategory.FINANCIAL

    # ========================================================================
    # Non-Financial Queries - Should Reject
    # ========================================================================

    def test_reject_sports_query(self):
        """Test that sports query is rejected."""
        query = "Who won the Super Bowl last year?"

        result = self.validator.validate(query)

        assert result.is_valid is False
        assert result.domain_category == DomainCategory.NON_FINANCIAL
        assert result.rejection_reason is not None
        assert "financial" in result.rejection_reason.lower()

    def test_reject_politics_query(self):
        """Test that politics query is rejected."""
        query = "What are the latest election results?"

        result = self.validator.validate(query)

        assert result.is_valid is False
        assert result.domain_category == DomainCategory.NON_FINANCIAL

    def test_reject_weather_query(self):
        """Test that weather query is rejected."""
        query = "What's the weather forecast for tomorrow?"

        result = self.validator.validate(query)

        assert result.is_valid is False
        assert result.domain_category == DomainCategory.NON_FINANCIAL

    def test_reject_entertainment_query(self):
        """Test that entertainment query is rejected."""
        query = "What movies are playing this weekend?"

        result = self.validator.validate(query)

        assert result.is_valid is False
        assert result.domain_category == DomainCategory.NON_FINANCIAL

    def test_reject_general_knowledge_query(self):
        """Test that general knowledge query is rejected."""
        query = "What is the capital of France?"

        result = self.validator.validate(query)

        assert result.is_valid is False
        assert result.domain_category == DomainCategory.NON_FINANCIAL

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_edge_case_mixed_query(self):
        """Test mixed query with both financial and non-financial elements."""
        query = "How did Apple stock perform during the Super Bowl season?"

        result = self.validator.validate(query)

        # Should be accepted but with lower confidence (AMBIGUOUS is acceptable)
        assert result.is_valid is True
        assert result.domain_category in [DomainCategory.FINANCIAL, DomainCategory.AMBIGUOUS]
        assert result.confidence_score < 0.9  # Lower confidence due to mixed topic

    def test_edge_case_unclear_query(self):
        """Test unclear query that could be financial or not."""
        query = "What are the trends in technology?"

        result = self.validator.validate(query)

        # Should be accepted (tech could mean tech stocks) but with penalty
        assert result.is_valid is True
        assert result.confidence_score < 0.7

    def test_edge_case_very_short_query(self):
        """Test very short query."""
        query = "AAPL price"

        result = self.validator.validate(query)

        assert result.is_valid is True
        assert result.domain_category in [DomainCategory.FINANCIAL, DomainCategory.AMBIGUOUS]

    def test_edge_case_empty_query(self):
        """Test empty query."""
        query = ""

        result = self.validator.validate(query)

        assert result.is_valid is False
        assert "empty" in result.rejection_reason.lower()

    # ========================================================================
    # Confidence Scoring
    # ========================================================================

    def test_confidence_score_high_for_clear_financial(self):
        """Test that clear financial queries get high confidence."""
        query = "Calculate the Sharpe ratio for SPY ETF"

        result = self.validator.validate(query)

        assert result.confidence_score >= 0.9

    def test_confidence_penalty_for_ambiguous(self):
        """Test that ambiguous queries get confidence penalty."""
        query = "How is Apple doing?"  # Ambiguous - company or fruit?

        result = self.validator.validate(query)

        if result.is_valid:
            assert result.confidence_penalty > 0
            assert result.confidence_score < 0.8

    # ========================================================================
    # Financial Entity Detection
    # ========================================================================

    def test_detect_ticker_symbol(self):
        """Test that ticker symbols are detected."""
        query = "What is TSLA's beta?"

        result = self.validator.validate(query)

        assert result.is_valid is True
        assert len(result.detected_entities) > 0
        assert any(entity['type'] == 'ticker' for entity in result.detected_entities)

    def test_detect_multiple_tickers(self):
        """Test that multiple tickers are detected."""
        query = "Compare AAPL, MSFT, and GOOGL returns"

        result = self.validator.validate(query)

        assert result.is_valid is True
        tickers = [e for e in result.detected_entities if e['type'] == 'ticker']
        assert len(tickers) >= 3

    def test_detect_financial_metrics(self):
        """Test that financial metrics are detected."""
        query = "Calculate correlation and volatility for my portfolio"

        result = self.validator.validate(query)

        assert result.is_valid is True
        metrics = [e for e in result.detected_entities if e['type'] == 'metric']
        assert len(metrics) >= 2

    # ========================================================================
    # Rejection Messages
    # ========================================================================

    def test_rejection_message_clarity(self):
        """Test that rejection messages are clear and helpful."""
        query = "Who is the president?"

        result = self.validator.validate(query)

        assert result.is_valid is False
        assert result.rejection_reason is not None
        assert len(result.rejection_reason) > 20  # Meaningful message
        # Should suggest what types of queries are accepted
        assert any(word in result.rejection_reason.lower()
                  for word in ['financial', 'market', 'stock', 'portfolio'])

    def test_rejection_message_includes_examples(self):
        """Test that rejection includes example of valid queries."""
        query = "What's for dinner?"

        result = self.validator.validate(query)

        assert result.is_valid is False
        # Message should guide user toward valid queries
        assert 'example' in result.rejection_reason.lower() or \
               'such as' in result.rejection_reason.lower() or \
               'like' in result.rejection_reason.lower()

    # ========================================================================
    # Language Detection
    # ========================================================================

    def test_detect_language_english_query(self):
        """Detect English query language."""
        query = "Calculate Sharpe ratio for AAPL in 2024"

        result = self.validator.validate(query)

        assert result.detected_language == "en"

    def test_detect_language_russian_query(self):
        """Detect Russian query language."""
        query = "Рассчитай коэффициент Шарпа для AAPL за 2024 год"

        result = self.validator.validate(query)

        assert result.detected_language == "ru"

    def test_detect_language_unknown_when_no_letters(self):
        """Fallback to unknown when no Latin/Cyrillic letters are present."""
        query = "12345 !!! ???"

        result = self.validator.validate(query)

        assert result.detected_language == "unknown"


# ============================================================================
# Integration with Other Validators
# ============================================================================

class TestDomainValidatorIntegration:
    """Integration tests for domain validator."""

    def test_domain_validator_before_golden_set(self):
        """Test that domain validation happens before golden set validation."""
        validator = DomainConstraintsValidator()

        # Non-financial query should be rejected before reaching golden set
        query = "What's the weather today?"
        result = validator.validate(query)

        assert result.is_valid is False
        # This would have wasted resources if passed to orchestrator

    def test_domain_validator_with_valid_financial_query(self):
        """Test that valid financial queries pass domain validation."""
        validator = DomainConstraintsValidator()

        query = "Calculate Sharpe ratio for SPY"
        result = validator.validate(query)

        assert result.is_valid is True
        # Can proceed to orchestrator
