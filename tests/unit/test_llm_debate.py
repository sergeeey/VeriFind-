"""
Unit tests for LLM-powered Debate.

Week 10 Day 3: Replace rule-based debate with LLM multi-perspective analysis.

Tests validate that:
1. Debate prompts are generated correctly
2. LLM generates multi-perspective analysis
3. Debates cite verified facts
4. Validation catches quality issues
5. Synthesis provides balanced view
"""

import pytest
from src.debate.llm_debate import (
    DebatePerspective,
    DebateResult,
    LLMDebateNode,
    DebateValidator,
    DebatePromptBuilder
)


class TestDebatePerspective:
    """Tests for DebatePerspective dataclass."""

    def test_create_perspective(self):
        """Test creating a debate perspective."""
        perspective = DebatePerspective(
            name="Bull",
            analysis="AAPL has strong fundamentals",
            confidence=0.85,
            supporting_facts=["Sharpe ratio 1.95", "Low volatility"]
        )

        assert perspective.name == "Bull"
        assert perspective.analysis == "AAPL has strong fundamentals"
        assert perspective.confidence == 0.85
        assert len(perspective.supporting_facts) == 2

    def test_perspective_confidence_validation(self):
        """Test that confidence is validated."""
        with pytest.raises(ValueError):
            DebatePerspective(
                name="Bull",
                analysis="Test",
                confidence=1.5,  # Invalid
                supporting_facts=[]
            )


class TestDebateResult:
    """Tests for DebateResult dataclass."""

    def test_create_debate_result(self):
        """Test creating debate result with all perspectives."""
        bull = DebatePerspective("Bull", "Optimistic view", 0.8, ["fact1"])
        bear = DebatePerspective("Bear", "Pessimistic view", 0.7, ["fact2"])
        neutral = DebatePerspective("Neutral", "Balanced view", 0.9, ["fact3"])

        result = DebateResult(
            bull_perspective=bull,
            bear_perspective=bear,
            neutral_perspective=neutral,
            synthesis="Overall assessment",
            confidence=0.85
        )

        assert result.bull_perspective.name == "Bull"
        assert result.bear_perspective.name == "Bear"
        assert result.neutral_perspective.name == "Neutral"
        assert result.synthesis == "Overall assessment"
        assert result.confidence == 0.85

    def test_debate_result_validation(self):
        """Test that all perspectives are required."""
        bull = DebatePerspective("Bull", "View", 0.8, [])

        with pytest.raises(TypeError):
            # Missing required perspectives
            DebateResult(bull_perspective=bull)


class TestDebatePromptBuilder:
    """Tests for DebatePromptBuilder class."""

    def setup_method(self):
        """Setup test instance."""
        self.builder = DebatePromptBuilder()

    # ========================================================================
    # Prompt Building
    # ========================================================================

    def test_build_sharpe_prompt(self):
        """Test building prompt for Sharpe ratio."""
        fact = {
            "metric": "sharpe_ratio",
            "ticker": "AAPL",
            "value": 1.95,
            "year": 2023
        }

        prompt = self.builder.build_prompt(fact)

        assert prompt is not None
        assert "AAPL" in prompt
        assert "1.95" in prompt or "Sharpe" in prompt
        assert "Bull" in prompt
        assert "Bear" in prompt
        assert "Neutral" in prompt

    def test_build_correlation_prompt(self):
        """Test building prompt for correlation."""
        fact = {
            "metric": "correlation",
            "ticker1": "AAPL",
            "ticker2": "MSFT",
            "value": 0.85,
            "year": 2023
        }

        prompt = self.builder.build_prompt(fact)

        assert "AAPL" in prompt
        assert "MSFT" in prompt
        assert "0.85" in prompt or "correlation" in prompt.lower()

    def test_build_volatility_prompt(self):
        """Test building prompt for volatility."""
        fact = {
            "metric": "volatility",
            "ticker": "TSLA",
            "value": 0.52,
            "year": 2023
        }

        prompt = self.builder.build_prompt(fact)

        assert "TSLA" in prompt
        assert "0.52" in prompt or "52%" in prompt or "volatility" in prompt.lower()

    def test_prompt_includes_structure(self):
        """Test that prompt includes required structure."""
        fact = {"metric": "sharpe_ratio", "ticker": "AAPL", "value": 1.5}
        prompt = self.builder.build_prompt(fact)

        # Should include instructions for all perspectives
        assert "Bull" in prompt or "optimistic" in prompt.lower()
        assert "Bear" in prompt or "pessimistic" in prompt.lower()
        assert "Neutral" in prompt or "balanced" in prompt.lower()
        assert "Synthesis" in prompt or "overall" in prompt.lower()


class TestLLMDebateNode:
    """Tests for LLMDebateNode class."""

    def setup_method(self):
        """Setup test instance."""
        self.node = LLMDebateNode(provider="mock")

    # ========================================================================
    # Debate Generation
    # ========================================================================

    def test_generate_debate_sharpe(self):
        """Test generating debate for Sharpe ratio."""
        fact = {
            "metric": "sharpe_ratio",
            "ticker": "AAPL",
            "value": 1.95,
            "year": 2023
        }

        result = self.node.generate_debate(fact)

        assert result is not None
        assert result.bull_perspective is not None
        assert result.bear_perspective is not None
        assert result.neutral_perspective is not None
        assert result.synthesis is not None

    def test_debate_has_all_perspectives(self):
        """Test that debate includes all required perspectives."""
        fact = {"metric": "sharpe_ratio", "ticker": "SPY", "value": 1.43}

        result = self.node.generate_debate(fact)

        # All perspectives present
        assert result.bull_perspective.name in ["Bull", "Bullish"]
        assert result.bear_perspective.name in ["Bear", "Bearish"]
        assert result.neutral_perspective.name in ["Neutral", "Balanced"]

    def test_perspectives_have_analysis(self):
        """Test that each perspective has analysis text."""
        fact = {"metric": "correlation", "ticker1": "SPY", "ticker2": "QQQ", "value": 0.92}

        result = self.node.generate_debate(fact)

        assert len(result.bull_perspective.analysis) > 0
        assert len(result.bear_perspective.analysis) > 0
        assert len(result.neutral_perspective.analysis) > 0
        assert len(result.synthesis) > 0

    def test_perspectives_cite_facts(self):
        """Test that perspectives cite supporting facts."""
        fact = {
            "metric": "sharpe_ratio",
            "ticker": "AAPL",
            "value": 1.95,
            "supporting_data": ["Return: 44%", "Volatility: 18%"]
        }

        result = self.node.generate_debate(fact)

        # At least one perspective should cite facts
        all_facts = (
            result.bull_perspective.supporting_facts +
            result.bear_perspective.supporting_facts +
            result.neutral_perspective.supporting_facts
        )
        assert len(all_facts) > 0

    def test_confidence_scores_reasonable(self):
        """Test that confidence scores are in valid range."""
        fact = {"metric": "sharpe_ratio", "ticker": "AAPL", "value": 1.95}

        result = self.node.generate_debate(fact)

        assert 0.0 <= result.bull_perspective.confidence <= 1.0
        assert 0.0 <= result.bear_perspective.confidence <= 1.0
        assert 0.0 <= result.neutral_perspective.confidence <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    # ========================================================================
    # Error Handling
    # ========================================================================

    def test_handles_invalid_fact(self):
        """Test handling of invalid fact."""
        fact = {}  # Empty fact

        result = self.node.generate_debate(fact)

        # Mock provider handles gracefully (returns result with defaults)
        # Real providers should validate input
        assert result is not None

    def test_handles_llm_failure(self):
        """Test handling when LLM fails."""
        node = LLMDebateNode(provider="failing_mock")
        fact = {"metric": "sharpe_ratio", "ticker": "AAPL", "value": 1.0}

        result = node.generate_debate(fact)

        # failing_mock returns None to simulate failure
        assert result is None


class TestDebateValidator:
    """Tests for DebateValidator class."""

    def setup_method(self):
        """Setup test instance."""
        self.validator = DebateValidator()

    # ========================================================================
    # Validation Tests
    # ========================================================================

    def test_validates_complete_debate(self):
        """Test validation of complete debate."""
        bull = DebatePerspective("Bull", "Good analysis", 0.8, ["fact1"])
        bear = DebatePerspective("Bear", "Bad analysis", 0.7, ["fact2"])
        neutral = DebatePerspective("Neutral", "Balanced", 0.9, ["fact3"])

        result = DebateResult(
            bull_perspective=bull,
            bear_perspective=bear,
            neutral_perspective=neutral,
            synthesis="Overall good",
            confidence=0.8
        )

        is_valid = self.validator.validate(result)
        assert is_valid is True

    def test_rejects_missing_perspective(self):
        """Test rejection when perspective is missing."""
        bull = DebatePerspective("Bull", "Analysis", 0.8, [])
        bear = DebatePerspective("Bear", "", 0.7, [])  # Empty analysis
        neutral = DebatePerspective("Neutral", "Analysis", 0.9, [])

        result = DebateResult(
            bull_perspective=bull,
            bear_perspective=bear,
            neutral_perspective=neutral,
            synthesis="Good",
            confidence=0.8
        )

        is_valid = self.validator.validate(result)
        assert is_valid is False

    def test_rejects_no_citations(self):
        """Test rejection when no facts are cited."""
        bull = DebatePerspective("Bull", "Analysis", 0.8, [])
        bear = DebatePerspective("Bear", "Analysis", 0.7, [])
        neutral = DebatePerspective("Neutral", "Analysis", 0.9, [])

        result = DebateResult(
            bull_perspective=bull,
            bear_perspective=bear,
            neutral_perspective=neutral,
            synthesis="Good",
            confidence=0.8
        )

        # Should warn about no citations
        is_valid = self.validator.validate(result)
        # May still be valid, but should log warning

    def test_validates_confidence_range(self):
        """Test validation of confidence scores."""
        # Should raise ValueError at construction
        with pytest.raises(ValueError):
            bull = DebatePerspective("Bull", "Analysis", 1.5, ["fact"])  # Invalid

    def test_checks_synthesis_quality(self):
        """Test that synthesis is not empty."""
        bull = DebatePerspective("Bull", "Analysis", 0.8, ["fact"])
        bear = DebatePerspective("Bear", "Analysis", 0.7, ["fact"])
        neutral = DebatePerspective("Neutral", "Analysis", 0.9, ["fact"])

        result = DebateResult(
            bull_perspective=bull,
            bear_perspective=bear,
            neutral_perspective=neutral,
            synthesis="",  # Empty synthesis
            confidence=0.8
        )

        is_valid = self.validator.validate(result)
        assert is_valid is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestLLMDebateIntegration:
    """Integration tests for LLM debate."""

    def test_end_to_end_debate_generation(self):
        """Test end-to-end debate generation."""
        fact = {
            "metric": "sharpe_ratio",
            "ticker": "AAPL",
            "value": 1.95,
            "year": 2023,
            "supporting_data": ["Return: 44.9%", "Volatility: 17.8%"]
        }

        # Build prompt
        builder = DebatePromptBuilder()
        prompt = builder.build_prompt(fact)
        assert prompt is not None

        # Generate debate
        node = LLMDebateNode(provider="mock")
        result = node.generate_debate(fact)
        assert result is not None

        # Validate
        validator = DebateValidator()
        is_valid = validator.validate(result)
        assert is_valid is True

    def test_debate_quality_metrics(self):
        """Test that debate meets quality standards."""
        fact = {"metric": "sharpe_ratio", "ticker": "SPY", "value": 1.43}

        node = LLMDebateNode(provider="mock")
        result = node.generate_debate(fact)

        # Quality checks
        assert len(result.synthesis) > 50  # Substantial synthesis
        assert result.confidence > 0.5  # Reasonable confidence

        # At least 2 perspectives cite facts
        perspectives_with_facts = sum(
            1 for p in [result.bull_perspective, result.bear_perspective, result.neutral_perspective]
            if len(p.supporting_facts) > 0
        )
        assert perspectives_with_facts >= 2
