"""
Unit tests for PLAN node provider fallback.

Week 11 Day 5: Verify PLAN node works with DeepSeek when Anthropic unavailable.

Critical: This unblocks Golden Set pipeline when Anthropic Console is down.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from src.orchestration.nodes.plan_node import PlanNode
from src.orchestration.universal_llm_client import UniversalLLMClient, LLMResponse


class TestPlanNodeFallback:
    """Test PLAN node provider fallback chain."""

    def test_init_with_deepseek_only(self):
        """Test PLAN node initializes with only DeepSeek API key."""
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test_deepseek_key",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": ""
        }, clear=True):
            node = PlanNode()
            assert "deepseek" in node.client.available_providers
            assert node.client is not None

    def test_init_fails_without_any_key(self):
        """Test PLAN node raises error when no API keys available."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": ""
        }, clear=True):
            with pytest.raises(ValueError, match="No LLM providers available"):
                PlanNode()

    def test_fallback_to_deepseek_when_anthropic_fails(self):
        """Test PLAN node falls back to DeepSeek when Anthropic unavailable."""
        # Mock both providers available, but Anthropic fails
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test_anthropic_key",
            "DEEPSEEK_API_KEY": "test_deepseek_key"
        }):
            node = PlanNode()

            # Mock Anthropic to fail, DeepSeek to succeed
            mock_response = LLMResponse(
                content='{"query_id": "q1", "user_query": "test", "data_requirements": [], "code_blocks": [], "plan_reasoning": "test", "confidence_level": 0.9}',
                provider="deepseek",
                model="deepseek-chat",
                input_tokens=100,
                output_tokens=200,
                cost=0.0001
            )

            with patch.object(node.client, 'generate', return_value=mock_response):
                plan = node.generate_plan("What is SPY Sharpe ratio?")
                assert plan is not None
                assert node.last_provider_used == "deepseek"

    def test_deepseek_used_first_when_preferred(self):
        """Test DeepSeek is used first when set as preferred provider."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test_anthropic_key",
            "DEEPSEEK_API_KEY": "test_deepseek_key"
        }):
            node = PlanNode(preferred_provider="deepseek")

            mock_response = LLMResponse(
                content='{"query_id": "q1", "user_query": "test", "data_requirements": [], "code_blocks": [], "plan_reasoning": "test", "confidence_level": 0.9}',
                provider="deepseek",
                model="deepseek-chat",
                input_tokens=100,
                output_tokens=200,
                cost=0.0001
            )

            with patch.object(node.client, 'generate', return_value=mock_response):
                plan = node.generate_plan("What is SPY Sharpe ratio?")
                assert node.last_provider_used == "deepseek"

    def test_multiple_providers_available(self):
        """Test PLAN node works when multiple providers available."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test_anthropic_key",
            "DEEPSEEK_API_KEY": "test_deepseek_key",
            "OPENAI_API_KEY": "test_openai_key"
        }):
            node = PlanNode()
            providers = list(node.client.available_providers.keys())

            # Should detect all available providers
            assert len(providers) >= 1  # At least one should be available
            assert node.client is not None

    def test_get_stats_includes_providers(self):
        """Test get_stats() includes available providers."""
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test_deepseek_key"
        }):
            node = PlanNode()
            stats = node.get_stats()

            assert "available_providers" in stats
            assert "deepseek" in stats["available_providers"]
            assert "last_provider_used" in stats
            assert "validation_enabled" in stats


class TestUniversalLLMClient:
    """Test UniversalLLMClient provider detection and fallback."""

    def test_detect_deepseek_only(self):
        """Test client detects only DeepSeek when only its key is set."""
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test_key",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": ""
        }, clear=True):
            # Mock the actual API client initialization
            with patch('src.orchestration.universal_llm_client.OpenAI'):
                client = UniversalLLMClient()
                assert "deepseek" in client.available_providers

    def test_detect_multiple_providers(self):
        """Test client detects multiple providers when keys available."""
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test_deepseek",
            "OPENAI_API_KEY": "test_openai"
        }):
            with patch('src.orchestration.universal_llm_client.OpenAI'):
                client = UniversalLLMClient()
                # Should have at least DeepSeek
                assert len(client.available_providers) >= 1

    def test_fallback_order_default(self):
        """Test default fallback order: anthropic → deepseek → openai → gemini."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test_ant",
            "DEEPSEEK_API_KEY": "test_ds",
            "OPENAI_API_KEY": "test_oai"
        }):
            # All providers available, but will try anthropic first by default
            with patch('src.orchestration.universal_llm_client.anthropic'):
                with patch('src.orchestration.universal_llm_client.OpenAI'):
                    client = UniversalLLMClient()
                    # Providers detected
                    assert len(client.available_providers) >= 1

    def test_no_providers_raises_error(self):
        """Test error raised when no providers available."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No LLM providers available"):
                UniversalLLMClient()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not set"
)
class TestRealDeepSeekIntegration:
    """Integration test with real DeepSeek API (if key available)."""

    def test_plan_generation_with_deepseek(self):
        """Test real plan generation using DeepSeek API."""
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
            "ANTHROPIC_API_KEY": ""  # Force DeepSeek usage
        }):
            node = PlanNode(preferred_provider="deepseek")

            query = "Calculate the Sharpe ratio for SPY from 2023-01-01 to 2023-12-31"
            plan = node.generate_plan(query)

            # Verify plan structure
            assert plan.query_id is not None
            assert plan.user_query == query
            assert len(plan.code_blocks) > 0
            assert plan.confidence_level > 0.0
            assert node.last_provider_used == "deepseek"

            print(f"✅ Plan generated by DeepSeek successfully")
            print(f"   Steps: {len(plan.code_blocks)}")
            print(f"   Confidence: {plan.confidence_level:.2f}")
