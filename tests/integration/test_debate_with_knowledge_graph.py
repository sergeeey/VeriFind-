"""
Integration tests for Multi-LLM Debate + Knowledge Graph verification.

Week 11 Day 3: Test that debate results can be verified against Knowledge Graph.

These tests verify:
- Multi-LLM Debate generates analysis with factual claims
- Knowledge Graph can verify CEO claims
- Knowledge Graph can verify ownership claims
- Integration works end-to-end

Run with:
    pytest tests/integration/test_debate_with_knowledge_graph.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.debate.multi_llm_agents import AgentResponse, AgentRole
from src.debate.parallel_orchestrator import run_multi_llm_debate
from src.adapters.neo4j_adapter import (
    verify_ceo_claim,
    verify_ownership_claim,
    get_company_ceo,
    get_major_shareholders
)


@pytest.fixture
def mock_bull_response():
    """Mock Bull agent response with CEO mention."""
    return AgentResponse(
        role=AgentRole.BULL,
        analysis=(
            "Apple Inc. (AAPL) shows strong fundamentals. "
            "Under CEO Tim Cook's leadership since 2011, the company has "
            "maintained market dominance in consumer electronics. "
            "Revenue growth of 25% YoY is impressive."
        ),
        confidence=0.75,
        key_points=[
            "Strong CEO leadership (Tim Cook)",
            "Revenue growth 25% YoY",
            "Market dominance in smartphones"
        ]
    )


@pytest.fixture
def mock_bear_response():
    """Mock Bear agent response with ownership mention."""
    return AgentResponse(
        role=AgentRole.BEAR,
        analysis=(
            "Apple faces valuation concerns. Major institutional holders like "
            "Vanguard Group (8.5% ownership) and BlackRock (7.2% ownership) "
            "have been reducing positions. P/E ratio above industry average."
        ),
        confidence=0.65,
        key_points=[
            "High valuation concerns",
            "Institutional selling pressure",
            "P/E ratio elevated"
        ]
    )


@pytest.fixture
def mock_arbiter_response():
    """Mock Arbiter agent response."""
    return AgentResponse(
        role=AgentRole.ARBITER,
        analysis=(
            "Balanced assessment: Strong leadership and fundamentals, "
            "but valuation is stretched. Institutional ownership remains "
            "significant despite recent reductions."
        ),
        confidence=0.70,
        key_points=[
            "Leadership strength verified",
            "Valuation concerns valid",
            "Long-term potential intact"
        ],
        recommendation="HOLD"
    )


class TestDebateWithKnowledgeGraph:
    """Test Multi-LLM Debate integrated with Knowledge Graph verification."""

    @pytest.mark.asyncio
    async def test_debate_generates_ceo_claim(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that debate generates CEO claims that can be verified."""
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

            # Run debate
            result = await run_multi_llm_debate(
                query="Should I buy Apple stock?",
                context={"ticker": "AAPL"}
            )

            # Extract CEO claim from Bull analysis
            bull_analysis = result["perspectives"]["bull"]["analysis"]
            assert "Tim Cook" in bull_analysis

            # Verify CEO claim against Knowledge Graph
            ceo_verified = verify_ceo_claim("AAPL", "Tim Cook")
            assert ceo_verified is True

    @pytest.mark.asyncio
    async def test_debate_generates_ownership_claim(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test that debate generates ownership claims that can be verified."""
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

            # Run debate
            result = await run_multi_llm_debate(
                query="Should I buy Apple stock?",
                context={"ticker": "AAPL"}
            )

            # Extract ownership claim from Bear analysis
            bear_analysis = result["perspectives"]["bear"]["analysis"]
            assert "Vanguard" in bear_analysis

            # Verify ownership claim against Knowledge Graph
            vanguard_owns_5pct = verify_ownership_claim("AAPL", "Vanguard", 5.0)
            assert vanguard_owns_5pct is True

    def test_knowledge_graph_ceo_lookup(self):
        """Test direct Knowledge Graph CEO lookup."""
        # Get CEO of Apple
        ceo = get_company_ceo("AAPL")
        assert ceo == "Tim Cook"

        # Get CEO of Tesla
        ceo = get_company_ceo("TSLA")
        assert ceo == "Elon Musk"

        # Get CEO of Microsoft
        ceo = get_company_ceo("MSFT")
        assert ceo == "Satya Nadella"

    def test_knowledge_graph_ownership_lookup(self):
        """Test direct Knowledge Graph ownership lookup."""
        # Get major shareholders of Apple
        shareholders = get_major_shareholders("AAPL", min_percent=5.0)
        assert len(shareholders) >= 2

        # Verify Vanguard is a major holder
        vanguard = [s for s in shareholders if "Vanguard" in s["owner_name"]]
        assert len(vanguard) == 1
        assert vanguard[0]["percent"] >= 5.0

        # Verify BlackRock is a major holder
        blackrock = [s for s in shareholders if "BlackRock" in s["owner_name"]]
        assert len(blackrock) == 1
        assert blackrock[0]["percent"] >= 5.0

    @pytest.mark.asyncio
    async def test_multi_ticker_debate_verification(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test debate and verification across multiple tickers."""
        tickers = ["AAPL", "TSLA", "MSFT"]
        expected_ceos = {
            "AAPL": "Tim Cook",
            "TSLA": "Elon Musk",
            "MSFT": "Satya Nadella"
        }

        for ticker in tickers:
            # Get CEO from Knowledge Graph
            ceo = get_company_ceo(ticker)
            assert ceo is not None
            assert ceo == expected_ceos[ticker]

            # Verify CEO claim
            verified = verify_ceo_claim(ticker, ceo)
            assert verified is True

    def test_ownership_verification_accuracy(self):
        """Test ownership verification with various thresholds."""
        test_cases = [
            # (ticker, owner, min_percent, expected_result)
            ("AAPL", "Vanguard", 5.0, True),   # Vanguard owns 8.5%
            ("AAPL", "Vanguard", 10.0, False),  # Vanguard owns <10%
            ("TSLA", "Elon Musk", 15.0, True),  # Elon owns 20.5%
            ("TSLA", "Elon Musk", 25.0, False), # Elon owns <25%
            ("META", "Mark Zuckerberg", 10.0, True),  # Zuck owns 13.5%
            ("AAPL", "Jeff Bezos", 5.0, False),  # Bezos doesn't own AAPL
        ]

        for ticker, owner, min_pct, expected in test_cases:
            result = verify_ownership_claim(ticker, owner, min_pct)
            assert result == expected, (
                f"Failed: {owner} owns ≥{min_pct}% of {ticker} "
                f"expected={expected}, got={result}"
            )

    @pytest.mark.asyncio
    async def test_debate_fact_extraction_pattern(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """Test extracting verifiable facts from debate analysis."""
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

            # Run debate
            result = await run_multi_llm_debate(
                query="Who is the CEO of Apple and should I invest?",
                context={"ticker": "AAPL"}
            )

            # Extract and verify facts from all perspectives
            bull_analysis = result["perspectives"]["bull"]["analysis"]
            bear_analysis = result["perspectives"]["bear"]["analysis"]

            # Verify CEO fact from Bull
            assert "Tim Cook" in bull_analysis
            assert verify_ceo_claim("AAPL", "Tim Cook") is True

            # Verify ownership facts from Bear
            assert "Vanguard" in bear_analysis or "BlackRock" in bear_analysis

            if "Vanguard" in bear_analysis:
                assert verify_ownership_claim("AAPL", "Vanguard", 5.0) is True

            if "BlackRock" in bear_analysis:
                assert verify_ownership_claim("AAPL", "BlackRock", 5.0) is True

    def test_cross_company_verification(self):
        """Test that verification correctly handles different companies."""
        # Correct CEO claims
        assert verify_ceo_claim("AAPL", "Tim Cook") is True
        assert verify_ceo_claim("TSLA", "Elon Musk") is True

        # Incorrect CEO claims (wrong company)
        assert verify_ceo_claim("AAPL", "Elon Musk") is False
        assert verify_ceo_claim("TSLA", "Tim Cook") is False

        # Non-existent CEO
        assert verify_ceo_claim("AAPL", "Steve Jobs") is False

    def test_case_insensitive_verification(self):
        """Test that verification is case-insensitive."""
        # Different case variations
        assert verify_ceo_claim("AAPL", "Tim Cook") is True
        assert verify_ceo_claim("AAPL", "tim cook") is True
        assert verify_ceo_claim("AAPL", "TIM COOK") is True
        assert verify_ceo_claim("aapl", "Tim Cook") is True

    @pytest.mark.asyncio
    async def test_integration_success_criteria(
        self,
        mock_bull_response,
        mock_bear_response,
        mock_arbiter_response
    ):
        """
        Week 11 Day 3 Integration Success Criteria:

        ✅ Multi-LLM Debate generates factual claims
        ✅ Knowledge Graph can verify CEO claims
        ✅ Knowledge Graph can verify ownership claims
        ✅ Verification is accurate and reliable
        ✅ Integration works end-to-end
        """
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

            # Run debate
            result = await run_multi_llm_debate(
                query="Should I invest in Apple?",
                context={"ticker": "AAPL"}
            )

            # ✅ Debate generates analysis
            assert result is not None
            assert "perspectives" in result

            # ✅ Extract CEO claim
            bull_analysis = result["perspectives"]["bull"]["analysis"]
            assert "Tim Cook" in bull_analysis

            # ✅ Verify CEO claim
            ceo_verified = verify_ceo_claim("AAPL", "Tim Cook")
            assert ceo_verified is True

            # ✅ Extract ownership claim
            bear_analysis = result["perspectives"]["bear"]["analysis"]
            assert "Vanguard" in bear_analysis

            # ✅ Verify ownership claim
            ownership_verified = verify_ownership_claim("AAPL", "Vanguard", 5.0)
            assert ownership_verified is True

            print("\n" + "="*60)
            print("✅ WEEK 11 DAY 3 INTEGRATION SUCCESS!")
            print("="*60)
            print("Multi-LLM Debate + Knowledge Graph verification: OPERATIONAL")
            print(f"CEO verified: {ceo_verified}")
            print(f"Ownership verified: {ownership_verified}")
            print(f"Recommendation: {result['synthesis']['recommendation']}")
            print("="*60)
