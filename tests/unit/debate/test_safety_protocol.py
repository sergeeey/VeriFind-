"""
Unit tests for Enhanced Multi-Agent Debate Safety Protocol.

Week 13 Day 5: Trust/Skeptic/Leader agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.debate.enhanced.safety_protocol import (
    TrustAgent,
    SkepticAgent,
    LeaderAgent,
    TrustCheck,
    SkepticChallenge,
    LeaderSynthesis
)
from src.debate.enhanced.specialists import SpecialistResponse, SpecialistRole


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_specialist_responses():
    """Mock specialist responses for testing."""
    return [
        SpecialistResponse(
            role=SpecialistRole.EARNINGS,
            analysis="Revenue grew 25% YoY to $120B. Strong earnings beat expectations.",
            recommendation="BUY",
            confidence=0.85,
            key_points=["Revenue +25%", "Earnings beat", "Strong margins"]
        ),
        SpecialistResponse(
            role=SpecialistRole.MARKET,
            analysis="Bullish technical pattern. Price broke resistance at $175.",
            recommendation="BUY",
            confidence=0.75,
            key_points=["Bullish breakout", "High volume", "RSI neutral"]
        ),
        SpecialistResponse(
            role=SpecialistRole.SENTIMENT,
            analysis="Positive news flow. Analyst upgrades and new product launch.",
            recommendation="BUY",
            confidence=0.70,
            key_points=["Positive sentiment", "Analyst upgrades", "Product launch"]
        ),
        SpecialistResponse(
            role=SpecialistRole.VALUATION,
            analysis="P/E of 28 is reasonable given growth. Fair value $180.",
            recommendation="HOLD",
            confidence=0.65,
            key_points=["P/E=28", "Fair value $180", "Slight premium"]
        ),
        SpecialistResponse(
            role=SpecialistRole.RISK,
            analysis="Regulatory risks manageable. Competition increasing.",
            recommendation="HOLD",
            confidence=0.60,
            key_points=["Regulatory OK", "Competition risk", "Downside limited"]
        )
    ]


@pytest.fixture
def mock_context():
    """Mock ground truth context."""
    return {
        "ticker": "AAPL",
        "current_price": 175.50,
        "earnings": {
            "revenue": 120e9,
            "growth_yoy": 0.25,
            "eps": 6.15
        },
        "valuation": {
            "pe_ratio": 28.5,
            "pb_ratio": 45.2
        }
    }


# ============================================================================
# Test TrustAgent
# ============================================================================

@pytest.mark.asyncio
async def test_trust_agent_init():
    """Test TrustAgent initialization."""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        agent = TrustAgent()
        # Updated to Claude Sonnet 4.5 (Week 13)
        assert agent.model == "claude-sonnet-4-5-20250929"
        assert agent.client is not None


@pytest.mark.asyncio
async def test_trust_agent_build_prompt(mock_specialist_responses, mock_context):
    """Test TrustAgent prompt building."""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        agent = TrustAgent()
        prompt = agent.build_prompt("Should I buy AAPL?", mock_specialist_responses, mock_context)

        # Check prompt contains key elements
        assert "TRUST AGENT" in prompt
        assert "Should I buy AAPL?" in prompt
        assert "EARNINGS ANALYST" in prompt
        assert "Revenue grew 25%" in prompt
        assert "verified_claims" in prompt
        assert "unverified_claims" in prompt


@pytest.mark.asyncio
async def test_trust_agent_check_success(mock_specialist_responses, mock_context):
    """Test TrustAgent successful fact-checking."""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        agent = TrustAgent()

        # Mock API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"verified_claims": ["Revenue grew 25%"], "unverified_claims": [], "trust_score": 0.9, "warnings": []}')]

        with patch.object(agent.client.messages, 'create', new=AsyncMock(return_value=mock_response)):
            result = await agent.check("Should I buy AAPL?", mock_specialist_responses, mock_context)

            assert isinstance(result, TrustCheck)
            assert result.trust_score == 0.9
            assert "Revenue grew 25%" in result.verified_claims
            assert len(result.unverified_claims) == 0


@pytest.mark.asyncio
async def test_trust_agent_check_with_warnings(mock_specialist_responses, mock_context):
    """Test TrustAgent with unverified claims."""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        agent = TrustAgent()

        # Mock API response with warnings
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"verified_claims": ["Revenue grew 25%"], "unverified_claims": ["Analyst consensus"], "trust_score": 0.6, "warnings": ["Unverified analyst ratings"]}')]

        with patch.object(agent.client.messages, 'create', new=AsyncMock(return_value=mock_response)):
            result = await agent.check("Should I buy AAPL?", mock_specialist_responses, mock_context)

            assert result.trust_score == 0.6
            assert "Analyst consensus" in result.unverified_claims
            assert len(result.warnings) == 1


@pytest.mark.asyncio
async def test_trust_agent_error_handling(mock_specialist_responses, mock_context):
    """Test TrustAgent error handling."""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        agent = TrustAgent()

        # Mock API error
        with patch.object(agent.client.messages, 'create', new=AsyncMock(side_effect=Exception("API Error"))):
            result = await agent.check("Should I buy AAPL?", mock_specialist_responses, mock_context)

            assert result.trust_score == 0.5  # Fallback
            assert len(result.unverified_claims) > 0


# ============================================================================
# Test SkepticAgent
# ============================================================================

@pytest.mark.asyncio
async def test_skeptic_agent_init():
    """Test SkepticAgent initialization."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = SkepticAgent()
        assert agent.model == "gpt-4-turbo-preview"
        assert agent.client is not None


@pytest.mark.asyncio
async def test_skeptic_agent_build_prompt(mock_specialist_responses):
    """Test SkepticAgent prompt building."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = SkepticAgent()
        prompt = agent.build_prompt("Should I buy AAPL?", mock_specialist_responses)

        # Check prompt contains key elements
        assert "SKEPTIC AGENT" in prompt
        assert "Should I buy AAPL?" in prompt
        assert "Specialist Consensus: BUY" in prompt  # 3 BUY, 2 HOLD
        assert "concerns" in prompt
        assert "weak_arguments" in prompt


@pytest.mark.asyncio
async def test_skeptic_agent_challenge_success(mock_specialist_responses):
    """Test SkepticAgent successful challenge."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = SkepticAgent()

        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"concerns": ["Valuation high"], "weak_arguments": [], "counterpoints": ["Competition risk"], "skepticism_level": 0.4}'))
        ]

        with patch.object(agent.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
            result = await agent.challenge("Should I buy AAPL?", mock_specialist_responses)

            assert isinstance(result, SkepticChallenge)
            assert result.skepticism_level == 0.4
            assert "Valuation high" in result.concerns
            assert "Competition risk" in result.counterpoints


@pytest.mark.asyncio
async def test_skeptic_agent_error_handling(mock_specialist_responses):
    """Test SkepticAgent error handling."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = SkepticAgent()

        # Mock API error
        with patch.object(agent.client.chat.completions, 'create', new=AsyncMock(side_effect=Exception("API Error"))):
            result = await agent.challenge("Should I buy AAPL?", mock_specialist_responses)

            assert result.skepticism_level == 0.5  # Fallback
            assert len(result.concerns) > 0


# ============================================================================
# Test LeaderAgent
# ============================================================================

@pytest.mark.asyncio
async def test_leader_agent_init():
    """Test LeaderAgent initialization."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = LeaderAgent()
        assert agent.model == "gpt-4-turbo-preview"
        assert agent.client is not None


@pytest.mark.asyncio
async def test_leader_agent_build_prompt(mock_specialist_responses):
    """Test LeaderAgent prompt building."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = LeaderAgent()

        trust_check = TrustCheck(
            verified_claims=["Revenue grew 25%"],
            unverified_claims=[],
            trust_score=0.9,
            warnings=[]
        )

        skeptic_challenge = SkepticChallenge(
            concerns=["Valuation high"],
            weak_arguments=[],
            counterpoints=["Competition risk"],
            skepticism_level=0.4
        )

        prompt = agent.build_prompt("Should I buy AAPL?", mock_specialist_responses, trust_check, skeptic_challenge)

        # Check prompt contains key elements
        assert "LEADER AGENT" in prompt
        assert "Should I buy AAPL?" in prompt
        assert "BUY=3, HOLD=2, SELL=0" in prompt
        assert "Trust Score: 90%" in prompt
        assert "Skepticism Level: 40%" in prompt


@pytest.mark.asyncio
async def test_leader_agent_synthesize_success(mock_specialist_responses):
    """Test LeaderAgent successful synthesis."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = LeaderAgent()

        trust_check = TrustCheck(
            verified_claims=["Revenue grew 25%"],
            unverified_claims=[],
            trust_score=0.9,
            warnings=[]
        )

        skeptic_challenge = SkepticChallenge(
            concerns=["Valuation high"],
            weak_arguments=[],
            counterpoints=["Competition risk"],
            skepticism_level=0.4
        )

        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"final_recommendation": "BUY", "confidence": 0.75, "consensus_level": 0.8, "key_insights": ["Strong growth"], "risk_reward_assessment": "Favorable", "summary": "Buy recommendation"}'))
        ]

        with patch.object(agent.client.chat.completions, 'create', new=AsyncMock(return_value=mock_response)):
            result = await agent.synthesize("Should I buy AAPL?", mock_specialist_responses, trust_check, skeptic_challenge)

            assert isinstance(result, LeaderSynthesis)
            assert result.final_recommendation == "BUY"
            assert result.confidence == 0.75
            assert result.consensus_level == 0.8


@pytest.mark.asyncio
async def test_leader_agent_error_handling_fallback(mock_specialist_responses):
    """Test LeaderAgent fallback to majority vote on error."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        agent = LeaderAgent()

        trust_check = TrustCheck(
            verified_claims=[],
            unverified_claims=[],
            trust_score=0.5,
            warnings=[]
        )

        skeptic_challenge = SkepticChallenge(
            concerns=[],
            weak_arguments=[],
            counterpoints=[],
            skepticism_level=0.5
        )

        # Mock API error
        with patch.object(agent.client.chat.completions, 'create', new=AsyncMock(side_effect=Exception("API Error"))):
            result = await agent.synthesize("Should I buy AAPL?", mock_specialist_responses, trust_check, skeptic_challenge)

            # Should fallback to majority vote (3 BUY > 2 HOLD)
            assert result.final_recommendation == "BUY"
            assert result.confidence == 0.4  # Low confidence due to error
            assert "Error in synthesis" in result.key_insights[0]
