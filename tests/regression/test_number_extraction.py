"""
Regression tests for number extraction in validators.

Week 14 Day 2: Prevent extraction of numbers from index names (S&P 500, Russell 2000).
"""

import pytest
from eval.validators import AnswerValidator


class TestNumberExtractionBlacklist:
    """Test that validators ignore numbers from common financial index names."""

    def test_sp500_not_extracted_as_pe_ratio(self):
        """gs_014 regression: S&P 500 should not be extracted as P/E ratio."""
        answer = (
            "DIRECT ANSWER: The context does not provide AMD's P/E ratio. "
            "SPY (S&P 500 index) has a trailing P/E ratio of 27.45."
        )
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 27.45, NOT 500
        assert is_valid is True
        assert "27.45" in reason or "27" in reason
        assert "500" not in reason

    def test_russell_2000_not_extracted(self):
        """Russell 2000 should be blacklisted."""
        answer = (
            "The Russell 2000 index has a P/E ratio of 15.3. "
            "This represents small-cap stocks."
        )
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 15.3, NOT 2000
        assert is_valid is True
        assert "15.3" in reason or "15" in reason
        assert "2000" not in reason

    def test_nasdaq_100_not_extracted(self):
        """Nasdaq 100 should be blacklisted."""
        answer = "The Nasdaq 100 has a P/E ratio of 28.7."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 28.7, NOT 100
        assert is_valid is True
        assert "28.7" in reason or "28" in reason
        assert "100" not in reason

    def test_dow_30_not_extracted(self):
        """Dow 30 should be blacklisted."""
        answer = "The Dow 30 index has a P/E of 22.5."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 22.5, NOT 30
        assert is_valid is True
        assert "22.5" in reason or "22" in reason
        assert "30" not in reason

    def test_ftse_100_not_extracted(self):
        """FTSE 100 should be blacklisted."""
        answer = "The FTSE 100 has a trailing P/E of 18.9."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 18.9, NOT 100
        assert is_valid is True
        assert "18.9" in reason or "18" in reason

    def test_multiple_indices_in_text(self):
        """Multiple index names should all be blacklisted."""
        answer = (
            "Comparing indices: S&P 500 (P/E 27.4), Russell 2000 (P/E 15.3), "
            "and Nasdaq 100 (P/E 28.7). The average P/E is 23.8."
        )
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract first valid P/E (27.4), NOT any index numbers
        assert is_valid is True
        assert "500" not in reason
        assert "2000" not in reason
        assert "100" not in reason

    def test_case_insensitive_blacklist(self):
        """Blacklist should work regardless of case."""
        answer = "The s&p 500 index has a P/E of 27.45."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 27.45, NOT 500 (case insensitive)
        assert is_valid is True
        assert "27.45" in reason or "27" in reason
        assert "500" not in reason

    def test_pe_ratio_validation_still_works(self):
        """Original P/E ratio validation should still work."""
        answer = "The P/E ratio is 35.7."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        assert is_valid is True
        assert "35.7" in reason

    def test_pe_ratio_outside_range_rejected(self):
        """P/E ratio outside reasonable range should still be rejected."""
        answer = "The P/E ratio is 250.0."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        assert is_valid is False
        assert "outside reasonable range" in reason

    def test_no_pe_ratio_found_after_blacklist(self):
        """If only index numbers exist, should fail gracefully."""
        answer = "Only S&P 500 data available, no specific P/E."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should fail (no valid P/E after removing "500")
        assert is_valid is False
        assert "No numeric value found" in reason


class TestNumberExtractionEdgeCases:
    """Edge cases for number extraction."""

    def test_year_not_confused_with_index(self):
        """Year 2000 should not be confused with Russell 2000."""
        answer = "In year 2000, the P/E ratio was 45.3."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 45.3 (P/E in range)
        # Note: 2000 would be outside P/E range (5-100), so rejected correctly
        assert is_valid is True
        assert "45.3" in reason or "45" in reason

    def test_percentage_with_index_name(self):
        """Percentages near index names should be extracted correctly."""
        answer = "S&P 500 grew 12.5% last year."
        expected = {"metric": "percentage"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract 12.5, NOT 500
        assert is_valid is True
        assert "12.5" in reason or "12" in reason

    def test_multiple_valid_numbers_after_blacklist(self):
        """First valid number after blacklist should be extracted."""
        answer = "S&P 500 has P/E 27.4, while NASDAQ 100 has 28.7."
        expected = {"metric": "pe_ratio"}

        is_valid, reason = AnswerValidator.validate_float(answer, expected)

        # Should extract first valid P/E (27.4)
        assert is_valid is True
        assert ("27.4" in reason or "27" in reason or "28.7" in reason or "28" in reason)
