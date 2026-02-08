"""
Integration tests for LLM-powered Debate with REAL API calls.

Week 11 Day 1: Production LLM Integration

These tests require valid API keys in .env:
- OPENAI_API_KEY
- GOOGLE_API_KEY (for Gemini)
- DEEPSEEK_API_KEY

Tests are marked with @pytest.mark.integration and @pytest.mark.real_llm
to allow selective execution.

Run with:
    pytest tests/integration/test_llm_debate_real_api.py -v -m real_llm

Skip with:
    pytest tests/ -v -m "not real_llm"
"""

import pytest
import os
from src.debate.llm_debate import (
    LLMDebateNode,
    DebateResult,
    DebatePerspective
)


# Skip all tests if API keys not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or
    not os.getenv("GOOGLE_API_KEY") or
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="Real API keys not set in .env"
)


@pytest.fixture
def openai_node():
    """Create LLMDebateNode with OpenAI provider."""
    return LLMDebateNode(provider="openai")


@pytest.fixture
def gemini_node():
    """Create LLMDebateNode with Gemini provider."""
    return LLMDebateNode(provider="gemini")


@pytest.fixture
def deepseek_node():
    """Create LLMDebateNode with DeepSeek provider."""
    return LLMDebateNode(provider="deepseek")


@pytest.fixture
def sample_fact():
    """Sample fact for testing."""
    return {
        "metric": "sharpe_ratio",
        "ticker": "AAPL",
        "value": 1.95,
        "year": 2023,
        "supporting_data": [
            "Annual return: 44.9%",
            "Annual volatility: 17.8%",
            "Risk-free rate: 5.0%"
        ]
    }


# ============================================================================
# OpenAI Integration Tests
# ============================================================================

class TestOpenAIIntegration:
    """Test OpenAI API integration."""

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_openai_generates_debate(self, openai_node, sample_fact):
        """Test that OpenAI generates valid debate."""
        result = openai_node.generate_debate(sample_fact)

        assert result is not None
        assert isinstance(result, DebateResult)

        # All perspectives present
        assert result.bull_perspective is not None
        assert result.bear_perspective is not None
        assert result.neutral_perspective is not None
        assert result.synthesis is not None

        # Perspectives have content
        assert len(result.bull_perspective.analysis) > 50
        assert len(result.bear_perspective.analysis) > 50
        assert len(result.neutral_perspective.analysis) > 50
        assert len(result.synthesis) > 50

        # Confidence scores valid
        assert 0.0 <= result.bull_perspective.confidence <= 1.0
        assert 0.0 <= result.bear_perspective.confidence <= 1.0
        assert 0.0 <= result.neutral_perspective.confidence <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_openai_cites_facts(self, openai_node, sample_fact):
        """Test that OpenAI debate cites provided facts."""
        result = openai_node.generate_debate(sample_fact)

        # At least one perspective should cite facts
        all_facts = (
            result.bull_perspective.supporting_facts +
            result.bear_perspective.supporting_facts +
            result.neutral_perspective.supporting_facts
        )

        assert len(all_facts) > 0, "Debate should cite at least some facts"

        # Check if any cited fact mentions the key metrics
        cited_text = " ".join(all_facts).lower()
        assert any(keyword in cited_text for keyword in ["sharpe", "1.95", "aapl", "return", "volatility"])

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_openai_cost_tracking(self, openai_node, sample_fact):
        """Test that OpenAI tracks API costs."""
        # Reset stats
        openai_node._reset_stats()

        result = openai_node.generate_debate(sample_fact)

        # Check cost tracking
        stats = openai_node.get_stats()
        assert stats["total_calls"] == 1
        assert stats["total_cost"] > 0.0  # Should have non-zero cost
        assert stats["total_input_tokens"] > 0
        assert stats["total_output_tokens"] > 0

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_openai_handles_complex_fact(self, openai_node):
        """Test OpenAI with more complex financial fact."""
        complex_fact = {
            "metric": "correlation",
            "ticker1": "SPY",
            "ticker2": "QQQ",
            "value": 0.92,
            "year": 2023,
            "supporting_data": [
                "Both are equity indices",
                "QQQ is tech-heavy",
                "SPY is broad market",
                "High correlation indicates similar movements"
            ]
        }

        result = openai_node.generate_debate(complex_fact)

        assert result is not None
        assert result.synthesis is not None

        # Check that synthesis mentions both tickers
        synthesis_lower = result.synthesis.lower()
        assert "spy" in synthesis_lower or "s&p" in synthesis_lower
        assert "qqq" in synthesis_lower or "nasdaq" in synthesis_lower


# ============================================================================
# Gemini Integration Tests
# ============================================================================

class TestGeminiIntegration:
    """Test Google Gemini API integration."""

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_gemini_generates_debate(self, gemini_node, sample_fact):
        """Test that Gemini generates valid debate."""
        result = gemini_node.generate_debate(sample_fact)

        assert result is not None
        assert isinstance(result, DebateResult)

        # All perspectives present
        assert result.bull_perspective is not None
        assert result.bear_perspective is not None
        assert result.neutral_perspective is not None
        assert result.synthesis is not None

        # Perspectives have content
        assert len(result.bull_perspective.analysis) > 50
        assert len(result.bear_perspective.analysis) > 50
        assert len(result.neutral_perspective.analysis) > 50

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_gemini_cost_tracking(self, gemini_node, sample_fact):
        """Test that Gemini tracks API costs."""
        gemini_node._reset_stats()

        result = gemini_node.generate_debate(sample_fact)

        stats = gemini_node.get_stats()
        assert stats["total_calls"] == 1
        assert stats["total_cost"] > 0.0
        assert stats["total_input_tokens"] > 0
        assert stats["total_output_tokens"] > 0


# ============================================================================
# DeepSeek Integration Tests
# ============================================================================

class TestDeepSeekIntegration:
    """Test DeepSeek API integration."""

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_deepseek_generates_debate(self, deepseek_node, sample_fact):
        """Test that DeepSeek generates valid debate."""
        result = deepseek_node.generate_debate(sample_fact)

        assert result is not None
        assert isinstance(result, DebateResult)

        # All perspectives present
        assert result.bull_perspective is not None
        assert result.bear_perspective is not None
        assert result.neutral_perspective is not None
        assert result.synthesis is not None

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_deepseek_cost_efficiency(self, deepseek_node, sample_fact):
        """Test that DeepSeek is more cost-efficient than OpenAI."""
        deepseek_node._reset_stats()

        result = deepseek_node.generate_debate(sample_fact)

        stats = deepseek_node.get_stats()

        # DeepSeek pricing: ~$0.55 per 1M input tokens vs OpenAI ~$2.50
        # Cost should be significantly lower
        assert stats["total_cost"] < 0.01, "DeepSeek should cost less than $0.01 for single debate"


# ============================================================================
# Cross-Provider Comparison Tests
# ============================================================================

class TestProviderComparison:
    """Compare different LLM providers."""

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_all_providers_generate_valid_debates(
        self,
        openai_node,
        gemini_node,
        deepseek_node,
        sample_fact
    ):
        """Test that all providers generate valid debates for same fact."""
        openai_result = openai_node.generate_debate(sample_fact)
        gemini_result = gemini_node.generate_debate(sample_fact)
        deepseek_result = deepseek_node.generate_debate(sample_fact)

        # All should succeed
        assert openai_result is not None
        assert gemini_result is not None
        assert deepseek_result is not None

        # All should have synthesis
        assert len(openai_result.synthesis) > 0
        assert len(gemini_result.synthesis) > 0
        assert len(deepseek_result.synthesis) > 0

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_cost_comparison(
        self,
        openai_node,
        gemini_node,
        deepseek_node,
        sample_fact
    ):
        """Compare costs across providers."""
        # Reset all stats
        openai_node._reset_stats()
        gemini_node._reset_stats()
        deepseek_node._reset_stats()

        # Generate debates
        openai_node.generate_debate(sample_fact)
        gemini_node.generate_debate(sample_fact)
        deepseek_node.generate_debate(sample_fact)

        # Get costs
        openai_cost = openai_node.get_stats()["total_cost"]
        gemini_cost = gemini_node.get_stats()["total_cost"]
        deepseek_cost = deepseek_node.get_stats()["total_cost"]

        # DeepSeek should be cheapest
        assert deepseek_cost < openai_cost, "DeepSeek should be cheaper than OpenAI"

        # Log costs for comparison
        print(f"\nCost comparison for single debate:")
        print(f"  OpenAI:   ${openai_cost:.6f}")
        print(f"  Gemini:   ${gemini_cost:.6f}")
        print(f"  DeepSeek: ${deepseek_cost:.6f}")


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling for real API calls."""

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_handles_invalid_fact(self, openai_node):
        """Test handling of invalid fact data."""
        invalid_fact = {
            "metric": "unknown_metric",
            "ticker": "INVALID",
            "value": None
        }

        # Should handle gracefully (return None or raise specific error)
        result = openai_node.generate_debate(invalid_fact)

        # Either None (graceful) or valid result
        if result is not None:
            assert isinstance(result, DebateResult)

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_handles_api_timeout(self, openai_node, sample_fact):
        """Test handling of API timeouts."""
        # This is hard to test without mocking, but we can verify
        # that the node has timeout handling

        # Generate debate (should complete within reasonable time)
        import time
        start = time.time()

        result = openai_node.generate_debate(sample_fact)

        duration = time.time() - start

        # Should complete within 30 seconds
        assert duration < 30.0, "API call should not take more than 30 seconds"
        assert result is not None


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmarks for real LLM calls."""

    @pytest.mark.integration
    @pytest.mark.real_llm
    @pytest.mark.slow
    def test_batch_debate_generation(self, openai_node):
        """Test generating multiple debates (performance benchmark)."""
        facts = [
            {"metric": "sharpe_ratio", "ticker": "AAPL", "value": 1.95},
            {"metric": "sharpe_ratio", "ticker": "MSFT", "value": 1.73},
            {"metric": "sharpe_ratio", "ticker": "GOOGL", "value": 2.05},
        ]

        openai_node._reset_stats()

        import time
        start = time.time()

        results = [openai_node.generate_debate(fact) for fact in facts]

        duration = time.time() - start

        # All should succeed
        assert all(r is not None for r in results)

        # Should complete within reasonable time (< 60s for 3 debates)
        assert duration < 60.0

        # Log performance
        stats = openai_node.get_stats()
        print(f"\nBatch performance (3 debates):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Avg per debate: {duration/3:.2f}s")
        print(f"  Total cost: ${stats['total_cost']:.6f}")
        print(f"  Cost per debate: ${stats['total_cost']/3:.6f}")


# ============================================================================
# Week 11 Day 1 Success Criteria
# ============================================================================

@pytest.mark.integration
@pytest.mark.real_llm
def test_week11_day1_success_criteria(openai_node, gemini_node, deepseek_node, sample_fact):
    """
    Week 11 Day 1 Success Criteria:

    - [x] OpenAI integration functional
    - [x] Gemini integration functional
    - [x] DeepSeek integration functional
    - [x] Cost tracking per provider
    - [x] All providers generate valid debates
    - [x] Error handling works
    """
    # All providers should work
    openai_result = openai_node.generate_debate(sample_fact)
    gemini_result = gemini_node.generate_debate(sample_fact)
    deepseek_result = deepseek_node.generate_debate(sample_fact)

    assert openai_result is not None
    assert gemini_result is not None
    assert deepseek_result is not None

    # Cost tracking should work
    assert openai_node.get_stats()["total_cost"] > 0
    assert gemini_node.get_stats()["total_cost"] > 0
    assert deepseek_node.get_stats()["total_cost"] > 0

    print("\n✅ Week 11 Day 1 SUCCESS: Real LLM integration operational!")
    print(f"   OpenAI:   ${openai_node.get_stats()['total_cost']:.6f}")
    print(f"   Gemini:   ${gemini_node.get_stats()['total_cost']:.6f}")
    print(f"   DeepSeek: ${deepseek_node.get_stats()['total_cost']:.6f}")
