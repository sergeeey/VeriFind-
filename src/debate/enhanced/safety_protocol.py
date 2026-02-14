"""
Safety Protocol for Enhanced Multi-Agent Debate.

Week 13 Day 5: Trust/Skeptic/Leader agents for quality control.

Safety Agents:
- TrustAgent: Fact-checking and claim verification
- SkepticAgent: Challenge groupthink and identify weak arguments
- LeaderAgent: Synthesize all perspectives into final decision

Prevents:
- Groupthink (all analysts agreeing without scrutiny)
- Hallucinations (unverified claims)
- Overconfidence (unjustified certainty)
"""

import os
import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

from .specialists import SpecialistResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class TrustCheck:
    """Result from TrustAgent fact-checking."""
    verified_claims: List[str]
    unverified_claims: List[str]
    trust_score: float  # 0.0-1.0
    warnings: List[str]


@dataclass
class SkepticChallenge:
    """Result from SkepticAgent critique."""
    concerns: List[str]
    weak_arguments: List[str]
    counterpoints: List[str]
    skepticism_level: float  # 0.0-1.0 (higher = more skeptical)


@dataclass
class LeaderSynthesis:
    """Final synthesis from LeaderAgent."""
    final_recommendation: str  # BUY|HOLD|SELL
    confidence: float  # 0.0-1.0
    consensus_level: float  # 0.0-1.0 (agreement among specialists)
    key_insights: List[str]
    risk_reward_assessment: str
    summary: str


# ============================================================================
# Trust Agent (Claude)
# ============================================================================

class TrustAgent:
    """
    Fact-checking agent - verifies claims and identifies hallucinations.

    Provider: Claude (strong reasoning for fact-checking)
    Role: Verify factual claims made by specialists
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize Trust agent with Claude."""
        self.model = model

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        if AsyncAnthropic is None:
            raise ImportError("anthropic package required")

        self.client = AsyncAnthropic(api_key=api_key)
        self.logger = logging.getLogger(__name__)

    def build_prompt(
        self,
        query: str,
        specialist_responses: List[SpecialistResponse],
        context: Dict[str, Any]
    ) -> str:
        """Build fact-checking prompt."""
        # Extract all claims from specialists
        all_analyses = "\n\n".join([
            f"**{resp.role.value.upper()} ANALYST:**\n{resp.analysis}\n"
            f"Key Points: {resp.key_points}"
            for resp in specialist_responses
        ])

        return f"""You are a TRUST AGENT. Verify factual claims and identify potential hallucinations.

Query: {query}

Specialist Analyses:
{all_analyses}

Available Context (Ground Truth):
{json.dumps(context, indent=2)}

Your task:
1. Extract specific factual claims from each analyst
2. Verify each claim against the provided context
3. Identify claims that cannot be verified (potential hallucinations)
4. Flag any contradictions between analysts
5. Assess overall trust score (0.0-1.0)

Return JSON:
{{
    "verified_claims": [
        "Revenue grew 25% YoY (verified from earnings report)",
        "P/E ratio is 18.5 (verified from data)"
    ],
    "unverified_claims": [
        "Expected to gain market share (speculation, no evidence)",
        "Analyst consensus is Buy (not provided in context)"
    ],
    "trust_score": 0.75,
    "warnings": [
        "Earnings analyst made unverified claim about future growth",
        "Sentiment analyst cited analyst ratings not in context"
    ]
}}

Be rigorous. Only mark claims as verified if explicitly supported by context."""

    async def check(
        self,
        query: str,
        specialist_responses: List[SpecialistResponse],
        context: Dict[str, Any]
    ) -> TrustCheck:
        """Run fact-checking on specialist analyses."""
        try:
            prompt = self.build_prompt(query, specialist_responses, context)

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.3,  # Low temp for factual task
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text
            data = json.loads(content)

            return TrustCheck(
                verified_claims=data.get("verified_claims", []),
                unverified_claims=data.get("unverified_claims", []),
                trust_score=float(data.get("trust_score", 0.5)),
                warnings=data.get("warnings", [])
            )

        except Exception as e:
            self.logger.error(f"Trust agent error: {e}", exc_info=True)
            return TrustCheck(
                verified_claims=[],
                unverified_claims=["Error in fact-checking"],
                trust_score=0.5,
                warnings=[f"Trust check failed: {str(e)}"]
            )


# ============================================================================
# Skeptic Agent (GPT-4)
# ============================================================================

class SkepticAgent:
    """
    Devil's advocate - challenges consensus and identifies weak arguments.

    Provider: GPT-4 (strong reasoning for critique)
    Role: Challenge groupthink, find flaws, present counterarguments
    """

    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """Initialize Skeptic agent with GPT-4."""
        self.model = model

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        if AsyncOpenAI is None:
            raise ImportError("openai package required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)

    def build_prompt(
        self,
        query: str,
        specialist_responses: List[SpecialistResponse]
    ) -> str:
        """Build skeptical challenge prompt."""
        # Summarize specialist consensus
        recommendations = [r.recommendation for r in specialist_responses if r.recommendation]
        consensus = max(set(recommendations), key=recommendations.count) if recommendations else "UNKNOWN"

        all_analyses = "\n\n".join([
            f"**{resp.role.value.upper()}:** {resp.recommendation} ({resp.confidence:.0%} confident)\n"
            f"Analysis: {resp.analysis[:200]}..."
            for resp in specialist_responses
        ])

        return f"""You are a SKEPTIC AGENT. Challenge the consensus and find weaknesses.

Query: {query}

Specialist Consensus: {consensus}

All Analyses:
{all_analyses}

Your task (play devil's advocate):
1. Identify weak or circular arguments
2. Find contradictions between analysts
3. Challenge assumptions (e.g., "growth will continue")
4. Present counterarguments to the consensus
5. Assess skepticism level (0.0 = no concerns, 1.0 = major concerns)

Return JSON:
{{
    "concerns": [
        "Earnings analyst assumes margin expansion will continue",
        "Valuation based on optimistic growth assumptions",
        "Risk analyst underweighted regulatory risk"
    ],
    "weak_arguments": [
        "Sentiment analyst: 'positive news' without specifics",
        "Market analyst: chart pattern not statistically significant"
    ],
    "counterpoints": [
        "Margins could compress due to competition",
        "Valuation rich by historical standards",
        "Technical breakout could be false signal"
    ],
    "skepticism_level": 0.65
}}

Be critical but fair. Find genuine weaknesses, not nitpicks."""

    async def challenge(
        self,
        query: str,
        specialist_responses: List[SpecialistResponse]
    ) -> SkepticChallenge:
        """Run skeptical critique on specialist analyses."""
        try:
            prompt = self.build_prompt(query, specialist_responses)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional skeptic and devil's advocate. Challenge weak arguments constructively."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1200,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return SkepticChallenge(
                concerns=data.get("concerns", []),
                weak_arguments=data.get("weak_arguments", []),
                counterpoints=data.get("counterpoints", []),
                skepticism_level=float(data.get("skepticism_level", 0.5))
            )

        except Exception as e:
            self.logger.error(f"Skeptic agent error: {e}", exc_info=True)
            return SkepticChallenge(
                concerns=["Error in skeptical review"],
                weak_arguments=[],
                counterpoints=[],
                skepticism_level=0.5
            )


# ============================================================================
# Leader Agent (GPT-4o or Claude)
# ============================================================================

class LeaderAgent:
    """
    Synthesis agent - combines all perspectives into final decision.

    Provider: GPT-4 (strong reasoning for synthesis)
    Role: Weigh all inputs (specialists + trust + skeptic) and make final call
    """

    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """Initialize Leader agent with GPT-4."""
        self.model = model

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        if AsyncOpenAI is None:
            raise ImportError("openai package required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)

    def build_prompt(
        self,
        query: str,
        specialist_responses: List[SpecialistResponse],
        trust_check: TrustCheck,
        skeptic_challenge: SkepticChallenge
    ) -> str:
        """Build synthesis prompt."""
        # Summarize specialists
        specialist_summary = "\n".join([
            f"- {resp.role.value.upper()}: {resp.recommendation} "
            f"({resp.confidence:.0%} confident)"
            for resp in specialist_responses
        ])

        # Count recommendations
        recommendations = [r.recommendation for r in specialist_responses if r.recommendation]
        buy_count = recommendations.count("BUY")
        hold_count = recommendations.count("HOLD")
        sell_count = recommendations.count("SELL")

        return f"""You are the LEADER AGENT. Synthesize all perspectives and make final decision.

Query: {query}

SPECIALIST RECOMMENDATIONS:
{specialist_summary}
Vote: BUY={buy_count}, HOLD={hold_count}, SELL={sell_count}

TRUST CHECK:
- Trust Score: {trust_check.trust_score:.0%}
- Verified: {len(trust_check.verified_claims)} claims
- Unverified: {len(trust_check.unverified_claims)} claims
- Warnings: {trust_check.warnings[:2] if trust_check.warnings else ['None']}

SKEPTIC CONCERNS:
- Skepticism Level: {skeptic_challenge.skepticism_level:.0%}
- Concerns: {skeptic_challenge.concerns[:3] if skeptic_challenge.concerns else ['None']}
- Counterpoints: {skeptic_challenge.counterpoints[:2] if skeptic_challenge.counterpoints else ['None']}

Your task:
1. Weigh all specialist opinions (give more weight to high-confidence, verified claims)
2. Consider trust score (downweight if many unverified claims)
3. Address skeptic concerns (are they valid? do they change the conclusion?)
4. Calculate consensus level (0.0-1.0, based on agreement)
5. Make final recommendation with adjusted confidence

Return JSON:
{{
    "final_recommendation": "BUY|HOLD|SELL",
    "confidence": 0.65,
    "consensus_level": 0.70,
    "key_insights": [
        "Strong earnings growth but high valuation",
        "Technical setup favorable, but sentiment mixed",
        "Downside risks manageable given reward potential"
    ],
    "risk_reward_assessment": "Favorable risk/reward at current levels (2:1 ratio)",
    "summary": "Final synthesis paragraph (2-3 sentences)"
}}

Be balanced. Don't just follow the majority - consider quality of arguments."""

    async def synthesize(
        self,
        query: str,
        specialist_responses: List[SpecialistResponse],
        trust_check: TrustCheck,
        skeptic_challenge: SkepticChallenge
    ) -> LeaderSynthesis:
        """Synthesize all perspectives into final decision."""
        try:
            prompt = self.build_prompt(query, specialist_responses, trust_check, skeptic_challenge)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior financial analyst synthesizing multiple expert opinions into a final investment decision."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return LeaderSynthesis(
                final_recommendation=data.get("final_recommendation", "HOLD"),
                confidence=float(data.get("confidence", 0.5)),
                consensus_level=float(data.get("consensus_level", 0.5)),
                key_insights=data.get("key_insights", []),
                risk_reward_assessment=data.get("risk_reward_assessment", ""),
                summary=data.get("summary", "")
            )

        except Exception as e:
            self.logger.error(f"Leader agent error: {e}", exc_info=True)
            # Fallback: simple majority vote
            recommendations = [r.recommendation for r in specialist_responses if r.recommendation]
            fallback_rec = max(set(recommendations), key=recommendations.count) if recommendations else "HOLD"

            return LeaderSynthesis(
                final_recommendation=fallback_rec,
                confidence=0.4,
                consensus_level=0.5,
                key_insights=["Error in synthesis - fallback to majority vote"],
                risk_reward_assessment="Unable to assess due to error",
                summary=f"Error in synthesis. Fallback recommendation: {fallback_rec}"
            )
