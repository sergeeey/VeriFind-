"""
Enhanced Multi-Agent Debate Orchestrator.

Week 13 Day 5: Coordinates 5 specialists + 3 safety agents.

Flow:
1. Run 5 specialists in parallel (Earnings, Market, Sentiment, Valuation, Risk)
2. TrustAgent: Fact-check all claims
3. SkepticAgent: Challenge consensus
4. LeaderAgent: Synthesize final decision

This ensures:
- No groupthink (Skeptic challenges)
- No hallucinations (Trust verifies)
- Balanced decision (Leader weighs all perspectives)
"""

import asyncio
import logging
from typing import Dict, Any, List
from dataclasses import dataclass

from .specialists import (
    EarningsAnalyst,
    MarketAnalyst,
    SentimentAnalyst,
    ValuationAnalyst,
    RiskAnalyst,
    SpecialistResponse
)
from .safety_protocol import (
    TrustAgent,
    SkepticAgent,
    LeaderAgent,
    TrustCheck,
    SkepticChallenge,
    LeaderSynthesis
)

logger = logging.getLogger(__name__)


# ============================================================================
# Enhanced Debate Result
# ============================================================================

@dataclass
class EnhancedDebateResult:
    """Full result from enhanced debate with safety checks."""
    # Specialist responses
    specialist_responses: List[SpecialistResponse]

    # Safety checks
    trust_check: TrustCheck
    skeptic_challenge: SkepticChallenge
    leader_synthesis: LeaderSynthesis

    # Summary metrics
    avg_confidence: float
    vote_distribution: Dict[str, int]  # {"BUY": 3, "HOLD": 2, "SELL": 0}
    consensus_level: float  # 0.0-1.0 (from leader)
    trust_score: float  # 0.0-1.0 (from trust agent)
    skepticism_level: float  # 0.0-1.0 (from skeptic)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "specialists": [
                {
                    "role": resp.role.value,
                    "recommendation": resp.recommendation,
                    "confidence": resp.confidence,
                    "analysis": resp.analysis,
                    "key_points": resp.key_points
                }
                for resp in self.specialist_responses
            ],
            "safety_checks": {
                "trust": {
                    "verified_claims": self.trust_check.verified_claims,
                    "unverified_claims": self.trust_check.unverified_claims,
                    "trust_score": self.trust_check.trust_score,
                    "warnings": self.trust_check.warnings
                },
                "skeptic": {
                    "concerns": self.skeptic_challenge.concerns,
                    "weak_arguments": self.skeptic_challenge.weak_arguments,
                    "counterpoints": self.skeptic_challenge.counterpoints,
                    "skepticism_level": self.skeptic_challenge.skepticism_level
                }
            },
            "final_decision": {
                "recommendation": self.leader_synthesis.final_recommendation,
                "confidence": self.leader_synthesis.confidence,
                "consensus_level": self.leader_synthesis.consensus_level,
                "key_insights": self.leader_synthesis.key_insights,
                "risk_reward_assessment": self.leader_synthesis.risk_reward_assessment,
                "summary": self.leader_synthesis.summary
            },
            "metrics": {
                "avg_confidence": self.avg_confidence,
                "vote_distribution": self.vote_distribution,
                "consensus_level": self.consensus_level,
                "trust_score": self.trust_score,
                "skepticism_level": self.skepticism_level
            }
        }


# ============================================================================
# Enhanced Orchestrator
# ============================================================================

class EnhancedDebateOrchestrator:
    """
    Orchestrates enhanced multi-agent debate with safety protocol.

    Architecture:
    - 5 specialists (parallel execution)
    - 3 safety agents (sequential: trust → skeptic → leader)

    Cost: ~$0.0063 per query (5x specialists + 3x safety agents)
    """

    def __init__(self):
        """Initialize all specialists and safety agents."""
        # Specialists (different LLMs for diversity)
        self.earnings_analyst = EarningsAnalyst()
        self.market_analyst = MarketAnalyst()
        self.sentiment_analyst = SentimentAnalyst()
        self.valuation_analyst = ValuationAnalyst()
        self.risk_analyst = RiskAnalyst()

        # Safety agents
        self.trust_agent = TrustAgent()
        self.skeptic_agent = SkepticAgent()
        self.leader_agent = LeaderAgent()

        self.logger = logging.getLogger(__name__)

    async def run_debate(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> EnhancedDebateResult:
        """
        Run full enhanced debate with safety protocol.

        Args:
            query: User query (e.g., "Should I buy AAPL?")
            context: Ground truth data (earnings, prices, etc.)

        Returns:
            EnhancedDebateResult with all specialist and safety agent outputs
        """
        self.logger.info(f"Starting enhanced debate for query: {query}")

        # Step 1: Run 5 specialists in parallel
        self.logger.info("Phase 1: Running 5 specialists in parallel...")
        specialist_responses = await self._run_specialists_parallel(query, context)

        if not specialist_responses:
            raise ValueError("All specialists failed to respond")

        self.logger.info(f"Received {len(specialist_responses)} specialist responses")

        # Step 2: Trust Agent - Fact-check claims
        self.logger.info("Phase 2: Trust Agent - Fact-checking claims...")
        trust_check = await self.trust_agent.check(query, specialist_responses, context)
        self.logger.info(f"Trust check complete: score={trust_check.trust_score:.2f}")

        # Step 3: Skeptic Agent - Challenge consensus
        self.logger.info("Phase 3: Skeptic Agent - Challenging consensus...")
        skeptic_challenge = await self.skeptic_agent.challenge(query, specialist_responses)
        self.logger.info(f"Skeptic challenge complete: skepticism={skeptic_challenge.skepticism_level:.2f}")

        # Step 4: Leader Agent - Synthesize final decision
        self.logger.info("Phase 4: Leader Agent - Synthesizing final decision...")
        leader_synthesis = await self.leader_agent.synthesize(
            query,
            specialist_responses,
            trust_check,
            skeptic_challenge
        )
        self.logger.info(f"Leader synthesis complete: {leader_synthesis.final_recommendation} "
                        f"(confidence={leader_synthesis.confidence:.2f})")

        # Calculate summary metrics
        avg_confidence = sum(r.confidence for r in specialist_responses) / len(specialist_responses)
        vote_distribution = self._count_votes(specialist_responses)

        result = EnhancedDebateResult(
            specialist_responses=specialist_responses,
            trust_check=trust_check,
            skeptic_challenge=skeptic_challenge,
            leader_synthesis=leader_synthesis,
            avg_confidence=avg_confidence,
            vote_distribution=vote_distribution,
            consensus_level=leader_synthesis.consensus_level,
            trust_score=trust_check.trust_score,
            skepticism_level=skeptic_challenge.skepticism_level
        )

        self.logger.info("Enhanced debate complete!")
        return result

    async def _run_specialists_parallel(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[SpecialistResponse]:
        """Run all 5 specialists in parallel for speed."""
        tasks = [
            self.earnings_analyst.analyze(query, context),
            self.market_analyst.analyze(query, context),
            self.sentiment_analyst.analyze(query, context),
            self.valuation_analyst.analyze(query, context),
            self.risk_analyst.analyze(query, context)
        ]

        # Gather with return_exceptions to handle failures gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failed specialists
        specialist_responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Specialist {i} failed: {result}")
            else:
                specialist_responses.append(result)

        return specialist_responses

    def _count_votes(self, responses: List[SpecialistResponse]) -> Dict[str, int]:
        """Count BUY/HOLD/SELL votes from specialists."""
        votes = {"BUY": 0, "HOLD": 0, "SELL": 0}
        for resp in responses:
            if resp.recommendation in votes:
                votes[resp.recommendation] += 1
        return votes


# ============================================================================
# Quick Test Function
# ============================================================================

async def test_enhanced_debate():
    """Quick test of enhanced debate orchestrator."""
    orchestrator = EnhancedDebateOrchestrator()

    # Mock context
    context = {
        "ticker": "AAPL",
        "current_price": 175.50,
        "earnings": {
            "revenue": 123.9e9,
            "eps": 2.18,
            "growth_yoy": 0.08
        },
        "valuation": {
            "pe_ratio": 29.5,
            "pb_ratio": 45.2
        }
    }

    result = await orchestrator.run_debate(
        query="Should I buy AAPL stock?",
        context=context
    )

    print("\n=== ENHANCED DEBATE RESULT ===")
    print(f"Final Recommendation: {result.leader_synthesis.final_recommendation}")
    print(f"Confidence: {result.leader_synthesis.confidence:.0%}")
    print(f"Consensus: {result.consensus_level:.0%}")
    print(f"Trust Score: {result.trust_score:.0%}")
    print(f"Skepticism: {result.skepticism_level:.0%}")
    print(f"Vote: {result.vote_distribution}")
    print(f"\nSummary: {result.leader_synthesis.summary}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_debate())
