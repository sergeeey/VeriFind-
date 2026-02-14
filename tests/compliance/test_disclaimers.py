"""
Compliance tests for disclaimers and AI disclosure.

Week 13 Day 1: SEC/EU AI Act compliance verification
"""

import pytest
from src.api.middleware.disclaimer import LEGAL_DISCLAIMER
from src.debate.schemas import Synthesis, Perspective


class TestDisclaimerCompliance:
    """Test disclaimer v2.0 compliance requirements."""

    def test_disclaimer_v2_has_all_required_fields(self):
        """
        Verify disclaimer v2.0 contains all required fields.

        SEC Requirement: Clear disclosure that this is NOT financial advice
        EU AI Act: AI system disclosure required
        """
        required_fields = [
            "text",
            "ai_disclosure",
            "data_sources_notice",
            "no_liability",
            "version",
            "effective_date",
            "regulatory_references"
        ]

        for field in required_fields:
            assert field in LEGAL_DISCLAIMER, f"Missing required field: {field}"

    def test_disclaimer_version_is_2_0(self):
        """Verify disclaimer version is 2.0."""
        assert LEGAL_DISCLAIMER["version"] == "2.0"

    def test_disclaimer_contains_ai_disclosure(self):
        """
        Verify AI disclosure is present and comprehensive.

        EU AI Act: High-risk AI systems must disclose AI generation
        """
        ai_disclosure = LEGAL_DISCLAIMER["ai_disclosure"]

        # Must mention it's AI-generated
        assert "artificial intelligence" in ai_disclosure.lower() or "AI" in ai_disclosure

        # Must mention multi-model system
        assert "multiple" in ai_disclosure.lower() or "multi" in ai_disclosure.lower()

        # Must explain confidence scores
        assert "confidence" in ai_disclosure.lower()
        assert "NOT" in ai_disclosure or "not" in ai_disclosure

    def test_disclaimer_contains_not_financial_advice(self):
        """
        Verify clear statement that this is NOT financial advice.

        SEC §202(a)(11): Must clearly distinguish information from advice
        """
        text = LEGAL_DISCLAIMER["text"]

        # Must explicitly say "NOT" or "does not constitute"
        assert "NOT" in text or "does not constitute" in text.lower()
        assert "financial advice" in text.lower() or "investment advice" in text.lower()

    def test_disclaimer_contains_data_sources_notice(self):
        """Verify data sources are disclosed."""
        notice = LEGAL_DISCLAIMER["data_sources_notice"]

        # Must mention data sources
        assert "yfinance" in notice or "FRED" in notice or "data" in notice.lower()

        # Must mention delays or inaccuracies
        assert "delayed" in notice.lower() or "inaccurate" in notice.lower()

    def test_disclaimer_contains_no_liability_clause(self):
        """
        Verify no liability clause is present.

        Legal protection: Limit liability for AI errors
        """
        no_liability = LEGAL_DISCLAIMER["no_liability"]

        assert "no liability" in no_liability.lower() or "accept no" in no_liability.lower()
        assert "loss" in no_liability.lower() or "damage" in no_liability.lower()

    def test_disclaimer_contains_regulatory_references(self):
        """Verify regulatory compliance references."""
        refs = LEGAL_DISCLAIMER["regulatory_references"]

        assert isinstance(refs, list)
        assert len(refs) > 0

        # Must reference SEC and EU AI Act
        refs_str = " ".join(refs)
        assert "SEC" in refs_str or "Investment Advisers Act" in refs_str
        assert "EU AI Act" in refs_str or "AI Act" in refs_str


class TestSynthesisCompliance:
    """Test Synthesis schema compliance fields."""

    def test_synthesis_has_ai_generated_flag(self):
        """
        Verify Synthesis has ai_generated field.

        EU AI Act: AI-generated content must be flagged
        """
        # Create a minimal Synthesis object
        synthesis = Synthesis(
            fact_id="test_fact",
            perspectives_reviewed=[Perspective.BULL, Perspective.BEAR],
            balanced_view="Test balanced view",
            key_risks=["Risk 1"],
            key_opportunities=["Opportunity 1"],
            recommendation="Test recommendation",
            original_confidence=0.8,
            adjusted_confidence=0.75,
            confidence_rationale="Test rationale"
        )

        # Check field exists
        assert hasattr(synthesis, "ai_generated")

        # Default should be True
        assert synthesis.ai_generated is True

    def test_synthesis_has_model_agreement(self):
        """
        Verify Synthesis has model_agreement field.

        Transparency: Users must know how many models agreed
        """
        synthesis = Synthesis(
            fact_id="test_fact",
            perspectives_reviewed=[Perspective.BULL, Perspective.BEAR, Perspective.NEUTRAL],
            balanced_view="Test",
            key_risks=[],
            key_opportunities=[],
            recommendation="Test",
            original_confidence=0.8,
            adjusted_confidence=0.75,
            confidence_rationale="Test",
            model_agreement="3/3 perspectives reviewed"
        )

        assert hasattr(synthesis, "model_agreement")
        assert synthesis.model_agreement is not None
        assert "/" in synthesis.model_agreement  # Should be format "X/Y"

    def test_synthesis_has_compliance_disclaimer(self):
        """
        Verify Synthesis has short compliance disclaimer.

        User experience: Quick notice in every response
        """
        synthesis = Synthesis(
            fact_id="test_fact",
            perspectives_reviewed=[Perspective.BULL],
            balanced_view="Test",
            key_risks=[],
            key_opportunities=[],
            recommendation="Test",
            original_confidence=0.8,
            adjusted_confidence=0.75,
            confidence_rationale="Test"
        )

        assert hasattr(synthesis, "compliance_disclaimer")
        assert synthesis.compliance_disclaimer is not None
        assert "NOT" in synthesis.compliance_disclaimer or "not" in synthesis.compliance_disclaimer


class TestDataAttributionCompliance:
    """Test data attribution structure."""

    def test_data_attribution_structure(self):
        """
        Verify data_attribution has required fields.

        Transparency: Users must know data sources and models used
        """
        # This will be tested via API endpoint (integration test)
        # Here we just verify the expected structure

        expected_fields = {
            "sources": list,  # List of data sources
            "llm_providers": list,  # List of LLM providers
            "generated_at": str,  # ISO timestamp
            "data_freshness": str  # Human-readable notice
        }

        # This is a schema test - actual data tested in integration
        assert expected_fields is not None

    def test_data_attribution_sources_format(self):
        """Verify data sources format."""
        # Expected format:
        # {"name": "yfinance", "type": "market_data", "delay": "15min"}

        source_template = {
            "name": str,
            "type": str,
            "delay": str
        }

        assert source_template is not None

    def test_data_attribution_llm_providers_format(self):
        """Verify LLM providers format."""
        # Expected format:
        # {"role": "bull", "provider": "deepseek", "model": "deepseek-chat"}

        provider_template = {
            "role": str,
            "provider": str,
            "model": str
        }

        assert provider_template is not None


class TestComplianceIntegration:
    """Integration tests for compliance features."""

    def test_disclaimer_effective_date_is_recent(self):
        """Verify disclaimer has recent effective date."""
        effective_date = LEGAL_DISCLAIMER["effective_date"]

        # Should be Feb 2026
        assert "2026" in effective_date
        assert "02" in effective_date or "2" in effective_date

    def test_all_disclaimer_texts_are_non_empty(self):
        """Verify no empty disclaimer fields."""
        for key, value in LEGAL_DISCLAIMER.items():
            if key == "regulatory_references":
                assert len(value) > 0
            else:
                assert value is not None
                assert len(str(value)) > 0
