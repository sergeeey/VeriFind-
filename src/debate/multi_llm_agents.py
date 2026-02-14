"""
Multi-LLM Debate Agents - Bull, Bear, Arbiter.

Week 12+: VeriFind commercial feature implementation.

Architecture:
- BullAgent: Optimistic analysis (DeepSeek - fast & cheap)
- BearAgent: Skeptical analysis (Anthropic Claude - critical thinking)
- ArbiterAgent: Balanced synthesis (OpenAI GPT-4 - reasoning)

Each agent runs in parallel for maximum speed.
Cost: ~$0.002 per query (DeepSeek $0.0003 + Claude $0.0015 + GPT-4 $0.0002)
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# LLM Provider SDKs
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class AgentRole(str, Enum):
    """Agent roles in debate."""
    BULL = "bull"
    BEAR = "bear"
    ARBITER = "arbiter"


@dataclass
class AgentResponse:
    """Response from a single agent."""
    role: AgentRole
    analysis: str
    confidence: float  # 0.0-1.0
    key_points: list[str]
    recommendation: Optional[str] = None  # BUY|HOLD|SELL (arbiter only)


@dataclass
class MultiLLMDebateResult:
    """Result from multi-LLM debate."""
    bull_response: AgentResponse
    bear_response: AgentResponse
    arbiter_response: AgentResponse
    overall_confidence: float
    recommendation: str  # BUY|HOLD|SELL
    risk_reward_ratio: str  # e.g., "60/40"
    cost_usd: float
    latency_ms: float


# ============================================================================
# Base Agent
# ============================================================================

class BaseAgent:
    """Base class for debate agents."""

    def __init__(self, role: AgentRole, provider: str, model: str):
        """
        Initialize agent.

        Args:
            role: Agent role (BULL/BEAR/ARBITER)
            provider: LLM provider (deepseek/anthropic/openai)
            model: Model name
        """
        self.role = role
        self.provider = provider
        self.model = model
        self.logger = logging.getLogger(__name__)

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """
        Build role-specific prompt.

        Args:
            query: User query
            context: Additional context (facts, data, etc.)

        Returns:
            Formatted prompt string
        """
        raise NotImplementedError("Subclass must implement build_prompt")

    async def analyze(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Run analysis from this agent's perspective.

        Args:
            query: User query
            context: Additional context

        Returns:
            AgentResponse with analysis
        """
        raise NotImplementedError("Subclass must implement analyze")


# ============================================================================
# Bull Agent (DeepSeek)
# ============================================================================

class BullAgent(BaseAgent):
    """
    Optimistic analyst - finds reasons to BUY/invest.

    Provider: DeepSeek (fast & cheap - $0.14/1M input, $0.28/1M output)
    Reasoning: Bullish analysis benefits from speed over deep reasoning.
    """

    def __init__(self, model: str = "deepseek-chat"):
        """Initialize Bull agent with DeepSeek."""
        super().__init__(AgentRole.BULL, "deepseek", model)

        # Initialize DeepSeek client (OpenAI-compatible)
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment")

        if AsyncOpenAI is None:
            raise ImportError("openai package required. Run: pip install openai")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build BULL perspective prompt."""
        return f"""You are a BULLISH financial analyst. Find reasons to BUY/invest.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your task:
1. Focus on: growth opportunities, competitive advantages, positive trends, bullish technical indicators
2. Be specific with numbers and facts from the context
3. Identify 3-5 key reasons to be optimistic
4. Provide a confidence score (0.0-1.0) based on strength of evidence

Return JSON:
{{
    "analysis": "Your bullish analysis here (2-3 paragraphs)",
    "confidence": 0.75,
    "key_points": [
        "Key bullish point 1",
        "Key bullish point 2",
        "Key bullish point 3"
    ]
}}

Be constructive but not unrealistic. Ground your analysis in the provided data."""

    async def analyze(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Run bullish analysis."""
        try:
            prompt = self.build_prompt(query, context)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional bullish financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            content = response.choices[0].message.content
            data = json.loads(content)

            return AgentResponse(
                role=AgentRole.BULL,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", [])
            )

        except Exception as e:
            self.logger.error(f"Bull agent error: {e}", exc_info=True)
            # Return fallback response
            return AgentResponse(
                role=AgentRole.BULL,
                analysis=f"Error generating bullish analysis: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable due to error"]
            )


# ============================================================================
# Bear Agent (Anthropic Claude)
# ============================================================================

class BearAgent(BaseAgent):
    """
    Skeptical analyst - finds reasons to SELL/avoid.

    Provider: Anthropic Claude (critical thinking - $3/1M input, $15/1M output)
    Reasoning: Claude excels at finding flaws and risks.
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize Bear agent with Claude."""
        super().__init__(AgentRole.BEAR, "anthropic", model)

        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        if AsyncAnthropic is None:
            raise ImportError("anthropic package required. Run: pip install anthropic")

        self.client = AsyncAnthropic(api_key=api_key)

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build BEAR perspective prompt."""
        return f"""You are a BEARISH financial analyst. Find reasons to SELL/avoid.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your task:
1. Focus on: risks, threats, overvaluation signals, negative trends, bearish indicators
2. Be specific with numbers and facts from the context
3. Identify 3-5 key concerns or red flags
4. Provide a confidence score (0.0-1.0) based on strength of evidence

Return JSON:
{{
    "analysis": "Your bearish analysis here (2-3 paragraphs)",
    "confidence": 0.65,
    "key_points": [
        "Key concern 1",
        "Key concern 2",
        "Key concern 3"
    ]
}}

Be critical but fair. Ground your analysis in the provided data."""

    async def analyze(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Run bearish analysis."""
        try:
            prompt = self.build_prompt(query, context)

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse JSON response
            content = response.content[0].text
            data = json.loads(content)

            return AgentResponse(
                role=AgentRole.BEAR,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", [])
            )

        except Exception as e:
            self.logger.error(f"Bear agent error: {e}", exc_info=True)
            # Return fallback response
            return AgentResponse(
                role=AgentRole.BEAR,
                analysis=f"Error generating bearish analysis: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable due to error"]
            )


# ============================================================================
# Arbiter Agent (OpenAI GPT-4)
# ============================================================================

class ArbiterAgent(BaseAgent):
    """
    Impartial synthesizer - provides balanced view and recommendation.

    Provider: OpenAI GPT-4 (reasoning - $2.50/1M input, $10/1M output)
    Reasoning: GPT-4 excels at synthesis and balanced reasoning.
    """

    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """Initialize Arbiter agent with GPT-4."""
        super().__init__(AgentRole.ARBITER, "openai", model)

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        if AsyncOpenAI is None:
            raise ImportError("openai package required. Run: pip install openai")

        self.client = AsyncOpenAI(api_key=api_key)

    def build_prompt(
        self,
        query: str,
        context: Dict[str, Any],
        bull_view: str,
        bear_view: str
    ) -> str:
        """Build ARBITER perspective prompt with bull/bear views."""
        return f"""You are an IMPARTIAL ARBITER. Synthesize these perspectives into a balanced view.

Query: {query}

Context:
{json.dumps(context, indent=2)}

BULL VIEW (Optimistic):
{bull_view}

BEAR VIEW (Pessimistic):
{bear_view}

Your task:
1. Provide a balanced synthesis of both perspectives
2. Calculate risk/reward ratio (e.g., "60/40" means 60% upside, 40% downside)
3. Give final recommendation: BUY, HOLD, or SELL
4. Provide overall confidence (0.0-1.0)
5. List 3-5 key takeaways

Return JSON:
{{
    "analysis": "Your balanced synthesis (2-3 paragraphs)",
    "confidence": 0.70,
    "key_points": [
        "Key takeaway 1",
        "Key takeaway 2",
        "Key takeaway 3"
    ],
    "recommendation": "BUY|HOLD|SELL",
    "risk_reward_ratio": "60/40"
}}

Be objective. Consider both bull and bear arguments fairly."""

    async def analyze(
        self,
        query: str,
        context: Dict[str, Any],
        bull_view: str = "",
        bear_view: str = ""
    ) -> AgentResponse:
        """Run arbiter synthesis."""
        try:
            prompt = self.build_prompt(query, context, bull_view, bear_view)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an impartial financial arbiter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            content = response.choices[0].message.content
            data = json.loads(content)

            return AgentResponse(
                role=AgentRole.ARBITER,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                recommendation=data.get("recommendation", "HOLD")
            )

        except Exception as e:
            self.logger.error(f"Arbiter agent error: {e}", exc_info=True)
            # Return fallback response
            return AgentResponse(
                role=AgentRole.ARBITER,
                analysis=f"Error generating synthesis: {str(e)}",
                confidence=0.3,
                key_points=["Synthesis unavailable due to error"],
                recommendation="HOLD"
            )
