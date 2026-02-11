"""
Integration tests for Multi-LLM Debate API endpoint.

Week 11 Day 2: Multi-LLM Parallel Debate Integration

These tests verify the /api/analyze-debate endpoint with:
- Mocked LLM providers (DeepSeek, Claude, GPT-4)
- Parallel execution validation
- Error handling
- Cost and latency tracking

Tests use pytest-mock to mock LLM API calls for isolation.

Run with:
    pytest tests/integration/test_multi_llm_debate_api.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Import main app
from src.api.main import app

# Import debate classes
from src.debate.multi_llm_agents import BullAgent, BearAgent, ArbiterAgent, AgentResponse, AgentRole
from src.debate.parallel_orchestrator import ParallelDebateOrchestrator, run_multi_llm_debate


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_bull_response():
    """Mock Bull agent response."""
    return AgentResponse(
        role=AgentRole.BULL,
        analysis="Strong growth potential with positive market momentum and increasing revenue.",
        confidence=0.75,
        key_points=["Revenue growth 25% YoY", "Strong market position", "Positive technical indicators"]
    )


@pytest.fixture
def mock_bear_response():
    """Mock Bear agent response."""
    return AgentResponse(
        role=AgentRole.BEAR,
        analysis="Significant risks including high valuation and regulatory concerns.",
        confidence=0.65,
        key_points=["P/E ratio above industry average", "Regulatory headwinds", "Market volatility increasing"]
    )


@pytest.fixture
def mock_arbiter_response():
    """Mock Arbiter agent response."""
    return AgentResponse(
        role=AgentRole.ARBITER,
        analysis="Balanced view considering both growth potential and material risks.",
        confidence=0.70,
        key_points=["Growth potential exists but risks are material", "Valuation reasonable at current price", "Market conditions uncertain"],
        recommendation="HOLD"
    )


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestMultiLLMDebateAPIEndpoint:
    """Test /api/analyze-debate endpoint."""

    @pytest.mark.asyncio
    async def test_successful_debate_execution(
        self,
        client,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test successful debate execution with all 3 agents."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            # Setup mocks
            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            # Make request
            response = client.post(
                "/api/analyze-debate",
                json={
                    "query": "Should I buy Tesla stock?",
                    "context": {"ticker": "TSLA", "price": 250.00}
                }
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()

            # Check structure
            assert "perspectives" in data
            assert "bull" in data["perspectives"]
            assert "bear" in data["perspectives"]
            assert "arbiter" in data["perspectives"]
            assert "synthesis" in data
            assert "metadata" in data

            # Check perspectives content
            assert data["perspectives"]["bull"]["provider"] == "deepseek"
            assert data["perspectives"]["bear"]["provider"] == "anthropic"
            assert data["perspectives"]["arbiter"]["provider"] == "openai"

            # Check recommendation
            assert data["perspectives"]["arbiter"]["recommendation"] == "HOLD"
            assert data["synthesis"]["recommendation"] == "HOLD"

            # Check metadata
            assert "cost_usd" in data["metadata"]
            assert "latency_ms" in data["metadata"]
            assert data["metadata"]["cost_usd"] > 0
            assert data["metadata"]["latency_ms"] > 0

    def test_missing_query_validation(self, client):
        """Test validation when query is missing."""
        response = client.post(
            "/api/analyze-debate",
            json={"context": {}}
        )

        assert response.status_code == 422  # Validation error

    def test_empty_query_validation(self, client):
        """Test validation when query is empty."""
        response = client.post(
            "/api/analyze-debate",
            json={"query": "", "context": {}}
        )

        assert response.status_code in [400, 422]

    def test_invalid_context_type(self, client):
        """Test validation when context is not a dict."""
        response = client.post(
            "/api/analyze-debate",
            json={"query": "Test query", "context": "invalid"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_api_keys_error(self, client):
        """Test handling of missing API keys."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.debate.multi_llm_agents.BullAgent.__init__') as mock_init:
                mock_init.side_effect = ValueError("DEEPSEEK_API_KEY not found")

                response = client.post(
                    "/api/analyze-debate",
                    json={"query": "Test query", "context": {}}
                )

                assert response.status_code == 500
                assert "DEEPSEEK_API_KEY" in response.json()["detail"]


# ============================================================================
# Parallel Orchestration Tests
# ============================================================================

class TestParallelOrchestration:
    """Test parallel execution of Bull/Bear agents."""

    @pytest.mark.asyncio
    async def test_bull_bear_parallel_execution(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that Bull and Bear execute in parallel."""
        import time

        async def slow_bull_analyze(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return mock_bull_response

        async def slow_bear_analyze(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return mock_bear_response

        async def arbiter_analyze(*args, **kwargs):
            return mock_arbiter_response

        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = slow_bull_analyze
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = slow_bear_analyze
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = arbiter_analyze
            MockArbiter.return_value = mock_arbiter

            start = time.time()
            result = await run_multi_llm_debate(
                query="Test query",
                context={}
            )
            duration = time.time() - start

            # Parallel execution should be ~0.2s (bull+bear parallel ~0.1s + arbiter ~0s)
            # NOT 0.2s sequential (bull 0.1s + bear 0.1s + arbiter 0s = 0.2s)
            assert duration < 0.15, f"Expected parallel execution ~0.1s, got {duration:.3f}s"

            # Verify result structure (dict)
            assert result["perspectives"]["bull"] is not None
            assert result["perspectives"]["bear"] is not None
            assert result["perspectives"]["arbiter"] is not None

    @pytest.mark.asyncio
    async def test_arbiter_receives_bull_bear_views(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that Arbiter receives Bull and Bear analyses."""
        arbiter_called_with = {}

        async def capture_arbiter_args(*args, **kwargs):
            arbiter_called_with.update(kwargs)
            return mock_arbiter_response

        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = capture_arbiter_args
            MockArbiter.return_value = mock_arbiter

            orchestrator = ParallelDebateOrchestrator()
            await orchestrator.run_debate(
                query="Test query",
                context={}
            )

            # Arbiter should receive bull_view and bear_view
            assert "bull_view" in arbiter_called_with
            assert "bear_view" in arbiter_called_with
            assert arbiter_called_with["bull_view"] == mock_bull_response.analysis
            assert arbiter_called_with["bear_view"] == mock_bear_response.analysis


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling in Multi-LLM debate."""

    @pytest.mark.asyncio
    async def test_bull_agent_api_failure(
        self,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test handling of Bull agent API failure."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            # Bull fails
            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(side_effect=Exception("DeepSeek API error"))
            MockBull.return_value = mock_bull

            # Bear and Arbiter succeed
            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            orchestrator = ParallelDebateOrchestrator()

            # Should raise or return error
            with pytest.raises(Exception):
                await orchestrator.run_debate(
                    query="Test query",
                    context={}
                )

    @pytest.mark.asyncio
    async def test_bear_agent_api_failure(
        self,
        mock_bull_response,
        mock_arbiter_response
    ):
        """Test handling of Bear agent API failure."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            # Bull succeeds
            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            # Bear fails
            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(side_effect=Exception("Claude API error"))
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            orchestrator = ParallelDebateOrchestrator()

            with pytest.raises(Exception):
                await orchestrator.run_debate(
                    query="Test query",
                    context={}
                )

    @pytest.mark.asyncio
    async def test_arbiter_agent_api_failure(
        self,
        mock_bull_response,
        mock_bear_response
    ):
        """Test handling of Arbiter agent API failure."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            # Arbiter fails
            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(side_effect=Exception("OpenAI API error"))
            MockArbiter.return_value = mock_arbiter

            orchestrator = ParallelDebateOrchestrator()

            with pytest.raises(Exception):
                await orchestrator.run_debate(
                    query="Test query",
                    context={}
                )


# ============================================================================
# Cost and Latency Tracking Tests
# ============================================================================

class TestCostAndLatencyTracking:
    """Test cost and latency tracking."""

    @pytest.mark.asyncio
    async def test_cost_aggregation(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that costs are aggregated correctly."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            result = await run_multi_llm_debate(
                query="Test query",
                context={}
            )

            # Total cost should be sum of all agents
            expected_cost = 0.0003 + 0.0015 + 0.0002  # $0.0020
            assert abs(result["metadata"]["cost_usd"] - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_latency_tracking(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that latency is tracked correctly."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            import time
            start = time.time()
            result = await run_multi_llm_debate(
                query="Test query",
                context={}
            )
            actual_duration = time.time() - start

            # Reported latency should be close to actual
            assert result["metadata"]["latency_ms"] > 0

            # Should be measured in milliseconds
            assert result["metadata"]["latency_ms"] < actual_duration * 1000 + 100  # +100ms margin


# ============================================================================
# Response Schema Validation Tests
# ============================================================================

class TestResponseSchemaValidation:
    """Test response schema validation."""

    @pytest.mark.asyncio
    async def test_response_has_required_fields(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that response has all required fields."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            result = await run_multi_llm_debate(
                query="Test query",
                context={}
            )

            # Check top-level fields
            assert "perspectives" in result
            assert "synthesis" in result
            assert "metadata" in result

            # Check perspectives fields
            for role in ["bull", "bear", "arbiter"]:
                assert role in result["perspectives"]
                perspective = result["perspectives"][role]
                assert "analysis" in perspective
                assert "confidence" in perspective
                assert "key_points" in perspective
                assert "provider" in perspective

            # Check synthesis fields
            assert "recommendation" in result["synthesis"]
            assert "overall_confidence" in result["synthesis"]
            assert "risk_reward_ratio" in result["synthesis"]

            # Check metadata fields
            assert "cost_usd" in result["metadata"]
            assert "latency_ms" in result["metadata"]
            assert "timestamp" in result["metadata"]

    @pytest.mark.asyncio
    async def test_confidence_scores_valid_range(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that confidence scores are in valid range [0, 1]."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            result = await run_multi_llm_debate(
                query="Test query",
                context={}
            )

            # Check all confidence scores
            assert 0 <= result["perspectives"]["bull"]["confidence"] <= 1
            assert 0 <= result["perspectives"]["bear"]["confidence"] <= 1
            assert 0 <= result["perspectives"]["arbiter"]["confidence"] <= 1
            assert 0 <= result["synthesis"]["overall_confidence"] <= 1

    @pytest.mark.asyncio
    async def test_recommendation_valid_values(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that recommendation is one of valid values."""
        with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
             patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
             patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

            mock_bull = AsyncMock()
            mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
            MockBull.return_value = mock_bull

            mock_bear = AsyncMock()
            mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
            MockBear.return_value = mock_bear

            mock_arbiter = AsyncMock()
            mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
            MockArbiter.return_value = mock_arbiter

            result = await run_multi_llm_debate(
                query="Test query",
                context={}
            )

            # Check recommendation is valid
            valid_recommendations = ["BUY", "HOLD", "SELL"]
            assert result["synthesis"]["recommendation"] in valid_recommendations

            if "recommendation" in result["perspectives"]["arbiter"]:
                assert result["perspectives"]["arbiter"]["recommendation"] in valid_recommendations


# ============================================================================
# Week 11 Day 2 Success Criteria
# ============================================================================

@pytest.mark.asyncio
async def test_week11_day2_success_criteria(
    mock_bull_response,
    mock_bear_response,
    mock_arbiter_response
):
    """
    Week 11 Day 2 Success Criteria:

    - [x] Multi-LLM Debate API endpoint functional
    - [x] Parallel execution of Bull/Bear agents
    - [x] Sequential execution of Arbiter after Bull/Bear
    - [x] Cost aggregation across all 3 providers
    - [x] Latency tracking
    - [x] Error handling for API failures
    - [x] Response schema validation
    - [x] Confidence scores in valid range
    - [x] Recommendations are valid (BUY/HOLD/SELL)
    """
    with patch('src.debate.parallel_orchestrator.BullAgent') as MockBull, \
         patch('src.debate.parallel_orchestrator.BearAgent') as MockBear, \
         patch('src.debate.parallel_orchestrator.ArbiterAgent') as MockArbiter:

        mock_bull = AsyncMock()
        mock_bull.analyze = AsyncMock(return_value=mock_bull_response)
        MockBull.return_value = mock_bull

        mock_bear = AsyncMock()
        mock_bear.analyze = AsyncMock(return_value=mock_bear_response)
        MockBear.return_value = mock_bear

        mock_arbiter = AsyncMock()
        mock_arbiter.analyze = AsyncMock(return_value=mock_arbiter_response)
        MockArbiter.return_value = mock_arbiter

        result = await run_multi_llm_debate(
            query="Should I buy Tesla stock?",
            context={"ticker": "TSLA", "price": 250.00}
        )

        # Verify all success criteria
        assert result is not None
        assert "perspectives" in result
        assert "synthesis" in result
        assert "metadata" in result

        assert result["metadata"]["cost_usd"] == 0.0020  # $0.0003 + $0.0015 + $0.0002
        assert result["metadata"]["latency_ms"] > 0

        assert result["synthesis"]["recommendation"] in ["BUY", "HOLD", "SELL"]

        assert 0 <= result["synthesis"]["overall_confidence"] <= 1

        print("\n✅ Week 11 Day 2 SUCCESS: Multi-LLM Debate API integration operational!")
        print(f"   Cost: ${result['metadata']['cost_usd']:.4f}")
        print(f"   Latency: {result['metadata']['latency_ms']:.1f}ms")
        print(f"   Recommendation: {result['synthesis']['recommendation']}")
        print(f"   Confidence: {result['synthesis']['overall_confidence']*100:.1f}%")
