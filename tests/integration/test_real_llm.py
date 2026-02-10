"""
Real LLM Integration Tests

Week 1 Day 3: Production Readiness
Tests with ACTUAL LLM APIs (costs money!)

Run only when:
- DEEPSEEK_API_KEY is set
- ANTHROPIC_API_KEY is set  
- Budget available (~$0.10 per test run)
"""

import pytest
import os
from unittest.mock import patch

# Skip all tests if no API keys
pytestmark = pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY") == "sk-test-fake-key-for-golden-set-testing",
    reason="Real DEEPSEEK_API_KEY not set. Set env var to run these tests."
)


class TestDeepSeekIntegration:
    """DeepSeek API integration tests"""
    
    @pytest.mark.real_llm
    def test_deepseek_simple_query(self):
        """Simple query to verify DeepSeek works"""
        from src.orchestration.universal_llm_client import UniversalLLMClient
        
        client = UniversalLLMClient(
            provider="deepseek",
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
        
        result = client.generate(
            prompt="What is 2+2? Answer with just the number.",
            max_tokens=10
        )
        
        assert result is not None
        assert "4" in result or "four" in result.lower()
        print(f"DeepSeek result: {result}")
    
    @pytest.mark.real_llm
    def test_deepseek_code_generation(self):
        """Code generation test"""
        from src.orchestration.universal_llm_client import UniversalLLMClient
        
        client = UniversalLLMClient(
            provider="deepseek",
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
        
        result = client.generate(
            prompt="Write Python code to calculate mean of a list: [1, 2, 3, 4, 5]",
            max_tokens=100
        )
        
        assert result is not None
        assert "mean" in result.lower() or "sum" in result.lower()
        print(f"Code generation result: {result[:200]}...")
    
    @pytest.mark.real_llm
    def test_deepseek_timeout_handling(self):
        """Test timeout handling"""
        from src.orchestration.universal_llm_client import UniversalLLMClient
        
        client = UniversalLLMClient(
            provider="deepseek",
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
        
        # Should handle timeout gracefully
        with pytest.raises(Exception):
            # Very short timeout should fail
            result = client.generate(
                prompt="Explain quantum physics in detail",
                max_tokens=2000,
                timeout=0.001  # Impossibly short
            )


class TestLLMFallbackChain:
    """LLM Fallback chain tests"""
    
    @pytest.mark.real_llm
    def test_fallback_when_primary_fails(self):
        """System falls back to Anthropic when DeepSeek fails"""
        from src.orchestration.universal_llm_client import UniversalLLMClient
        
        # Only run if we have both keys
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")
        
        client = UniversalLLMClient(
            provider="deepseek",  # Will try deepseek first
            api_key="invalid-key-to-force-fallback",  # Force failure
            fallback_provider="anthropic",
            fallback_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        result = client.generate(
            prompt="Say hello",
            max_tokens=10
        )
        
        assert result is not None
        print(f"Fallback result: {result}")


class TestGoldenSetRealLLM:
    """Golden Set with real LLM (expensive!)"""
    
    @pytest.mark.real_llm
    @pytest.mark.slow
    def test_single_golden_set_query(self):
        """Run single Golden Set query with real LLM"""
        from src.orchestration.orchestrator import APEOrchestrator
        
        orchestrator = APEOrchestrator(
            claude_api_key=os.getenv("ANTHROPIC_API_KEY") or "fake",
            enable_debate=False,
            skip_plan=False  # Real planning
        )
        
        result = orchestrator.run(
            query_id="test_real_001",
            query_text="Calculate the Sharpe ratio for AAPL using 2024 data"
        )
        
        assert result is not None
        assert "sharpe" in str(result).lower()
        print(f"Golden Set result: {result}")


class TestCostTracking:
    """Verify cost tracking works with real APIs"""
    
    @pytest.mark.real_llm
    def test_cost_tracking_live(self):
        """Track actual costs from LLM calls"""
        from src.orchestration.universal_llm_client import UniversalLLMClient
        from src.api.cost_tracking import CostTracker
        
        tracker = CostTracker()
        
        client = UniversalLLMClient(
            provider="deepseek",
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
        
        # Make a call
        result = client.generate(
            prompt="Calculate 10 * 10",
            max_tokens=20
        )
        
        # Verify cost was tracked
        costs = tracker.get_costs()
        assert "deepseek" in costs
        assert costs["deepseek"]["calls"] >= 1
        print(f"Costs tracked: {costs}")
