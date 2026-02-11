"""
Tests for Multi-LLM Debate System.

Week 12+: Tests for parallel Bull/Bear/Arbiter debate.

Test coverage:
- Individual agents (Bull, Bear, Arbiter)
- Parallel orchestrator
- API endpoint
- Error handling
- Cost/latency metrics
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.debate.multi_llm_agents import (
    BullAgent,
    BearAgent,
    ArbiterAgent,
    AgentResponse,
    AgentRole,
    MultiLLMDebateResult
)
from src.debate.parallel_orchestrator import ParallelDebateOrchestrator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_bull_response():
    """Mock bull agent response."""
    return AgentResponse(
        role=AgentRole.BULL,
        analysis="Strong growth potential with positive momentum...",
        confidence=0.75,
        key_points=[
            "Revenue growth 25% YoY",
            "Strong market position",
            "Positive technical indicators"
        ]
    )


@pytest.fixture
def mock_bear_response():
    """Mock bear agent response."""
    return AgentResponse(
        role=AgentRole.BEAR,
        analysis="Significant risks including high valuation and market headwinds...",
        confidence=0.65,
        key_points=[
            "P/E ratio above industry average",
            "Regulatory concerns",
            "Market volatility increasing"
        ]
    )


@pytest.fixture
def mock_arbiter_response():
    """Mock arbiter agent response."""
    return AgentResponse(
        role=AgentRole.ARBITER,
        analysis="Balanced view considering both growth potential and risks...",
        confidence=0.70,
        key_points=[
            "Growth potential exists but risks are material",
            "Valuation reasonable at current price",
            "Market conditions uncertain"
        ],
        recommendation="HOLD"
    )


@pytest.fixture
def sample_query():
    """Sample financial query."""
    return "Should I buy Tesla stock?"


@pytest.fixture
def sample_context():
    """Sample context data."""
    return {
        "ticker": "TSLA",
        "current_price": 250.00,
        "52w_high": 299.00,
        "52w_low": 101.81,
        "market_cap": "795B"
    }


# ============================================================================
# Bull Agent Tests
# ============================================================================

@pytest.mark.skipif(
    True,  # Skip by default (requires API keys)
    reason="Requires DEEPSEEK_API_KEY"
)
@pytest.mark.asyncio
async def test_bull_agent_real_api(sample_query, sample_context):
    """Test Bull agent with real DeepSeek API."""
    agent = BullAgent()
    response = await agent.analyze(sample_query, sample_context)

    assert response.role == AgentRole.BULL
    assert len(response.analysis) > 0
    assert 0.0 <= response.confidence <= 1.0
    assert len(response.key_points) >= 1


@pytest.mark.asyncio
async def test_bull_agent_mock():
    """Test Bull agent with mocked API."""
    with patch('src.debate.multi_llm_agents.AsyncOpenAI') as mock_openai:
        # Mock API response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "analysis": "Strong bullish case with revenue growth and market expansion.",
            "confidence": 0.80,
            "key_points": ["Revenue growth", "Market expansion", "Strong fundamentals"]
        }
        '''
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        agent = BullAgent()
        agent.client = mock_client
        response = await agent.analyze("Test query", {})

        assert response.role == AgentRole.BULL
        assert "bullish" in response.analysis.lower() or "growth" in response.analysis.lower()
        assert response.confidence == 0.80
        assert len(response.key_points) == 3


@pytest.mark.asyncio
async def test_bull_agent_error_handling():
    """Test Bull agent handles API errors gracefully."""
    with patch('src.debate.multi_llm_agents.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        mock_openai.return_value = mock_client

        agent = BullAgent()
        agent.client = mock_client
        response = await agent.analyze("Test query", {})

        # Should return fallback response
        assert response.role == AgentRole.BULL
        assert "error" in response.analysis.lower()
        assert response.confidence < 0.5  # Low confidence on error


# ============================================================================
# Bear Agent Tests
# ============================================================================

@pytest.mark.skipif(
    True,  # Skip by default (requires API keys)
    reason="Requires ANTHROPIC_API_KEY"
)
@pytest.mark.asyncio
async def test_bear_agent_real_api(sample_query, sample_context):
    """Test Bear agent with real Claude API."""
    agent = BearAgent()
    response = await agent.analyze(sample_query, sample_context)

    assert response.role == AgentRole.BEAR
    assert len(response.analysis) > 0
    assert 0.0 <= response.confidence <= 1.0
    assert len(response.key_points) >= 1


@pytest.mark.asyncio
async def test_bear_agent_mock():
    """Test Bear agent with mocked API."""
    with patch('src.debate.multi_llm_agents.AsyncAnthropic') as mock_anthropic:
        # Mock API response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '''
        {
            "analysis": "Significant bearish concerns including overvaluation and risks.",
            "confidence": 0.70,
            "key_points": ["Overvaluation", "Market risks", "Regulatory headwinds"]
        }
        '''
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        agent = BearAgent()
        agent.client = mock_client
        response = await agent.analyze("Test query", {})

        assert response.role == AgentRole.BEAR
        assert "bearish" in response.analysis.lower() or "risk" in response.analysis.lower()
        assert response.confidence == 0.70
        assert len(response.key_points) == 3


# ============================================================================
# Arbiter Agent Tests
# ============================================================================

@pytest.mark.skipif(
    True,  # Skip by default (requires API keys)
    reason="Requires OPENAI_API_KEY"
)
@pytest.mark.asyncio
async def test_arbiter_agent_real_api(sample_query, sample_context):
    """Test Arbiter agent with real GPT-4 API."""
    agent = ArbiterAgent()
    response = await agent.analyze(
        query=sample_query,
        context=sample_context,
        bull_view="Strong growth potential...",
        bear_view="Significant risks..."
    )

    assert response.role == AgentRole.ARBITER
    assert len(response.analysis) > 0
    assert 0.0 <= response.confidence <= 1.0
    assert response.recommendation in ["BUY", "HOLD", "SELL"]


@pytest.mark.asyncio
async def test_arbiter_agent_mock():
    """Test Arbiter agent with mocked API."""
    with patch('src.debate.multi_llm_agents.AsyncOpenAI') as mock_openai:
        # Mock API response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "analysis": "Balanced assessment considering both bull and bear views.",
            "confidence": 0.75,
            "key_points": ["Growth vs Risk", "Valuation reasonable", "Market uncertain"],
            "recommendation": "HOLD",
            "risk_reward_ratio": "55/45"
        }
        '''
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        agent = ArbiterAgent()
        agent.client = mock_client
        response = await agent.analyze(
            query="Test",
            context={},
            bull_view="Bullish",
            bear_view="Bearish"
        )

        assert response.role == AgentRole.ARBITER
        assert response.recommendation == "HOLD"
        assert response.confidence == 0.75


# ============================================================================
# Parallel Orchestrator Tests
# ============================================================================

@pytest.mark.asyncio
async def test_parallel_orchestrator_mock(
    mock_bull_response,
    mock_bear_response,
    mock_arbiter_response,
    sample_query,
    sample_context
):
    """Test parallel orchestrator with mocked agents."""
    orchestrator = ParallelDebateOrchestrator()

    # Mock all agents
    orchestrator.bull_agent.analyze = AsyncMock(return_value=mock_bull_response)
    orchestrator.bear_agent.analyze = AsyncMock(return_value=mock_bear_response)
    orchestrator.arbiter_agent.analyze = AsyncMock(return_value=mock_arbiter_response)

    # Run debate
    result = await orchestrator.run_debate(sample_query, sample_context)

    # Verify result structure
    assert isinstance(result, MultiLLMDebateResult)
    assert result.bull_response == mock_bull_response
    assert result.bear_response == mock_bear_response
    assert result.arbiter_response == mock_arbiter_response
    assert result.recommendation == "HOLD"
    assert 0.0 <= result.overall_confidence <= 1.0
    assert result.latency_ms > 0
    assert result.cost_usd > 0


@pytest.mark.asyncio
async def test_parallel_orchestrator_speed(
    mock_bull_response,
    mock_bear_response,
    mock_arbiter_response,
    sample_query,
    sample_context
):
    """Test that parallel execution is faster than sequential."""
    orchestrator = ParallelDebateOrchestrator()

    # Mock agents with delays
    async def slow_bull(*args, **kwargs):
        await asyncio.sleep(0.1)
        return mock_bull_response

    async def slow_bear(*args, **kwargs):
        await asyncio.sleep(0.1)
        return mock_bear_response

    async def slow_arbiter(*args, **kwargs):
        await asyncio.sleep(0.1)
        return mock_arbiter_response

    orchestrator.bull_agent.analyze = slow_bull
    orchestrator.bear_agent.analyze = slow_bear
    orchestrator.arbiter_agent.analyze = slow_arbiter

    # Run debate
    import time
    start = time.time()
    result = await orchestrator.run_debate(sample_query, sample_context)
    duration = time.time() - start

    # Should be ~0.2s (bull+bear parallel, then arbiter)
    # NOT 0.3s (sequential)
    assert duration < 0.25, f"Parallel execution too slow: {duration:.2f}s"
    assert result.latency_ms < 250


@pytest.mark.asyncio
async def test_orchestrator_to_dict(
    mock_bull_response,
    mock_bear_response,
    mock_arbiter_response
):
    """Test orchestrator dict conversion."""
    result = MultiLLMDebateResult(
        bull_response=mock_bull_response,
        bear_response=mock_bear_response,
        arbiter_response=mock_arbiter_response,
        overall_confidence=0.70,
        recommendation="HOLD",
        risk_reward_ratio="55/45",
        cost_usd=0.002,
        latency_ms=3500
    )

    orchestrator = ParallelDebateOrchestrator()
    result_dict = orchestrator.to_dict(result)

    # Verify structure
    assert "perspectives" in result_dict
    assert "bull" in result_dict["perspectives"]
    assert "bear" in result_dict["perspectives"]
    assert "arbiter" in result_dict["perspectives"]
    assert "synthesis" in result_dict
    assert "metadata" in result_dict
    assert result_dict["metadata"]["cost_usd"] == 0.002
    assert result_dict["metadata"]["latency_ms"] == 3500


# ============================================================================
# API Endpoint Tests
# ============================================================================
# Note: API endpoint integration tests moved to tests/integration/
# These require FastAPI test client fixture from conftest.py
