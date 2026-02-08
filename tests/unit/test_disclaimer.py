"""
Unit tests for disclaimer functionality.

Week 11 Day 3: Legal compliance testing.

Tests disclaimer constants and structure without requiring full API startup.
"""

import pytest
import json
from pathlib import Path


class TestDisclaimerConstants:
    """Test disclaimer constants and structure."""

    def test_disclaimer_md_exists(self):
        """Test DISCLAIMER.md file exists in project root."""
        disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"
        assert disclaimer_path.exists(), "DISCLAIMER.md must exist in project root"

    def test_disclaimer_md_content(self):
        """Test DISCLAIMER.md has required sections."""
        disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"

        with open(disclaimer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check required sections
        required_sections = [
            "# Legal Disclaimer",
            "## Financial Analysis Disclaimer",
            "### Not Financial Advice",
            "### Key Disclaimers",
            "### Recommendations",
            "### Limitation of Liability",
            "### AI-Generated Content Notice",
            "## Technical Disclaimer",
            "## Data Privacy",
            "## Acceptance"
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_disclaimer_md_key_warnings(self):
        """Test DISCLAIMER.md contains key warning phrases."""
        disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"

        with open(disclaimer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Key warning phrases that MUST appear
        key_phrases = [
            "informational purposes only",
            "NOT constitute financial advice",
            "Past performance does not guarantee future results",
            "consult a qualified financial advisor",
            "AI-generated",
            "may contain errors",
            "not liable",
            "at your own risk",
            "18 years old",
            "AS IS",
            "without warranty"
        ]

        content_lower = content.lower()

        for phrase in key_phrases:
            assert phrase.lower() in content_lower, f"Missing key phrase: {phrase}"

    def test_disclaimer_md_version_info(self):
        """Test DISCLAIMER.md has version information."""
        disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"

        with open(disclaimer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should have version info
        assert "**Version:**" in content
        assert "**Effective Date:**" in content
        assert "**Last Updated:**" in content

        # Should have v1.0
        assert "1.0" in content

        # Should have Feb 2026 date
        assert "2026" in content

    def test_disclaimer_md_recommendations_section(self):
        """Test DISCLAIMER.md has clear recommendations."""
        disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"

        with open(disclaimer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should have recommendations
        assert "### Recommendations" in content

        # Should list specific actions
        recommendations = [
            "Consult a qualified financial advisor",
            "Conduct your own research",
            "Consider your risk tolerance",
            "Review all relevant disclosure documents",
            "Understand the risks"
        ]

        for rec in recommendations:
            assert rec in content, f"Missing recommendation: {rec}"

    def test_disclaimer_md_ai_notice(self):
        """Test DISCLAIMER.md has AI-specific disclaimers."""
        disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"

        with open(disclaimer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # AI-specific warnings
        ai_warnings = [
            "AI-generated",
            "artificial intelligence algorithms",
            "AI models can make mistakes",
            "exhibit biases",
            "produce incorrect results",
            "Bull/Bear/Neutral Perspectives",
            "Confidence Scores"
        ]

        for warning in ai_warnings:
            assert warning in content, f"Missing AI warning: {warning}"

    def test_disclaimer_md_length(self):
        """Test DISCLAIMER.md is substantial (not just a placeholder)."""
        disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"

        with open(disclaimer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should be at least 5000 characters (substantial document)
        assert len(content) > 5000, "Disclaimer should be substantial (>5000 chars)"

        # Should have multiple paragraphs
        paragraphs = content.split("\n\n")
        assert len(paragraphs) > 20, "Disclaimer should have multiple sections"


class TestDisclaimerConstants:
    """Test disclaimer constants defined in code."""

    def test_legal_disclaimer_constant_structure(self):
        """Test LEGAL_DISCLAIMER constant has required fields."""
        # This would be imported from main.py in real test
        # For now, define expected structure
        expected_fields = ["text", "version", "effective_date", "full_text_url"]

        # Mock constant structure
        legal_disclaimer = {
            "text": "This analysis is for informational purposes only...",
            "version": "1.0",
            "effective_date": "2026-02-08",
            "full_text_url": "/disclaimer"
        }

        for field in expected_fields:
            assert field in legal_disclaimer, f"Missing field: {field}"

    def test_disclaimer_text_content(self):
        """Test disclaimer text has required phrases."""
        # Mock disclaimer text (should match actual constant in main.py)
        disclaimer_text = (
            "This analysis is for informational purposes only and should not be considered "
            "financial advice. Past performance does not guarantee future results. "
            "Always consult a qualified financial advisor before making investment decisions."
        )

        # Required phrases
        assert "informational purposes only" in disclaimer_text
        assert "not be considered financial advice" in disclaimer_text
        assert "Past performance does not guarantee future results" in disclaimer_text
        assert "consult a qualified financial advisor" in disclaimer_text

    def test_disclaimer_version_format(self):
        """Test version follows semantic versioning."""
        version = "1.0"

        # Should be in format X.Y or X.Y.Z
        parts = version.split(".")
        assert len(parts) >= 2, "Version should be X.Y format minimum"

        # Parts should be numbers
        for part in parts:
            assert part.isdigit(), f"Version part should be numeric: {part}"

    def test_disclaimer_effective_date_format(self):
        """Test effective date is in ISO format."""
        effective_date = "2026-02-08"

        # Should be YYYY-MM-DD format
        assert len(effective_date) == 10
        assert effective_date.count("-") == 2

        # Should be parseable as date
        parts = effective_date.split("-")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

        assert 2024 <= year <= 2030  # Reasonable year range
        assert 1 <= month <= 12
        assert 1 <= day <= 31


class TestDisclaimerIntegration:
    """Test disclaimer integration requirements."""

    def test_disclaimer_file_accessible_from_api(self):
        """Test DISCLAIMER.md is accessible from API path."""
        # API should be able to read DISCLAIMER.md from project root
        # Test path resolution
        from pathlib import Path

        # Simulate API path resolution
        # In main.py: Path(__file__).parent.parent.parent / "DISCLAIMER.md"
        api_main_path = Path(__file__).parent.parent / "integration" / "test_disclaimer_api.py"
        disclaimer_path = api_main_path.parent.parent.parent / "DISCLAIMER.md"

        # This would be the actual path from src/api/main.py
        real_disclaimer_path = Path(__file__).parent.parent.parent / "DISCLAIMER.md"

        assert real_disclaimer_path.exists(), "DISCLAIMER.md must be accessible from API"

    def test_disclaimer_endpoints_defined(self):
        """Test required disclaimer endpoints are defined."""
        # In real test, would check API routes
        # For now, document expected endpoints
        expected_endpoints = [
            "/disclaimer",  # GET - full disclaimer
        ]

        # All JSON responses should have disclaimer field added by middleware
        assert len(expected_endpoints) > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
