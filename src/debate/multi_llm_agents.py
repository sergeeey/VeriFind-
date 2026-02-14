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
# Cost Constants (Week 13 Day 1: Compliance)
# ============================================================================

# Token costs as of Feb 2026 (USD per 1K tokens)
COST_PER_1K_TOKENS = {
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost for LLM API call.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    if model not in COST_PER_1K_TOKENS:
        logger.warning(f"Unknown model '{model}' for cost calculation, using zero cost")
        return 0.0

    pricing = COST_PER_1K_TOKENS[model]
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    return input_cost + output_cost


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
    # Week 13 Day 1: Cost tracking
    input_tokens: int = 0
    output_tokens: int = 0


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

            # Week 13 Day 2: Extract token usage BEFORE parsing (survives JSON errors)
            usage = response.usage
            in_tok = usage.prompt_tokens if usage else 0
            out_tok = usage.completion_tokens if usage else 0

            # Parse JSON response
            content = response.choices[0].message.content

            try:
                data = json.loads(content)
            except json.JSONDecodeError as json_err:
                self.logger.warning(f"{self.__class__.__name__} JSON parse error: {json_err}")
                self.logger.warning(f"Raw content (first 200 chars): {content[:200]}")
                # Fallback: use raw content as analysis, but preserve usage
                data = {
                    "analysis": content,
                    "confidence": 0.5,
                    "key_points": ["Raw response (JSON parse failed)"]
                }

            return AgentResponse(
                role=AgentRole.BULL,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                input_tokens=in_tok,
                output_tokens=out_tok
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
        # Check if context has meaningful data
        has_data = context and any(
            v for k, v in context.items()
            if k not in ['query', 'timestamp'] and v
        )

        if has_data:
            instruction = "Ground your analysis in the provided data."
        else:
            instruction = """Even without perfect data, provide bearish analysis based on:
- Historical patterns and common risks for this type of query
- General market concerns and structural headwinds
- Potential data limitations and transparency issues
- Valuation concerns and competitive threats

DO NOT say "I cannot analyze" or "no data available". Provide substantive bearish perspective."""

        return f"""You are a BEARISH financial analyst. Find reasons to SELL/avoid.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your task:
1. Focus on: risks, threats, overvaluation signals, negative trends, bearish indicators
2. Be specific with numbers and facts from the context (if available)
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

{instruction}"""

    async def analyze(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Run bearish analysis."""
        try:
            prompt = self.build_prompt(query, context)

            # Week 13 Day 2: Debug logging for Bear agent failures
            self.logger.debug(f"Bear agent prompt length: {len(prompt)} chars")

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Week 13 Day 2: Validate response before parsing
            if not response.content or len(response.content) == 0:
                raise ValueError("Anthropic API returned empty content array")

            content = response.content[0].text
            self.logger.debug(f"Bear agent raw response length: {len(content)} chars")

            if not content or content.strip() == "":
                raise ValueError("Anthropic API returned empty text content")

            # Week 13 Day 2: Try to extract JSON from response
            # Claude sometimes wraps JSON in markdown code blocks
            json_content = content.strip()
            if json_content.startswith("```json"):
                json_content = json_content.split("```json")[1].split("```")[0].strip()
            elif json_content.startswith("```"):
                json_content = json_content.split("```")[1].split("```")[0].strip()

            data = json.loads(json_content)

            # Week 13 Day 2: Extract token usage (Anthropic format)
            usage = response.usage
            in_tok = usage.input_tokens if usage else 0
            out_tok = usage.output_tokens if usage else 0

            return AgentResponse(
                role=AgentRole.BEAR,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                input_tokens=in_tok,
                output_tokens=out_tok
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"Bear agent JSON parse error: {e}")
            self.logger.error(f"Raw content (first 500 chars): {content[:500] if 'content' in locals() else 'N/A'}")
            # Return fallback response
            return AgentResponse(
                role=AgentRole.BEAR,
                analysis=f"Error parsing bearish analysis JSON: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable due to JSON parsing error"]
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
        return f"""You are an IMPARTIAL ARBITER. Your PRIMARY task: answer the user's question directly using data from analyses below.

CRITICAL: Answer the specific question FIRST with concrete numbers/facts, THEN provide synthesis.

Query: {query}

Context:
{json.dumps(context, indent=2)}

BULL VIEW (Optimistic):
{bull_view}

BEAR VIEW (Pessimistic):
{bear_view}

Your task:
1. Extract the DIRECT ANSWER to the user's question from the analyses (e.g., "TSLA volatility: 45.2%")
2. If both analyses agree on data, state it immediately
3. If they disagree on numbers, present both values and explain the difference
4. THEN provide balanced synthesis of perspectives
5. Calculate risk/reward ratio (e.g., "60/40")
6. Give final recommendation: BUY, HOLD, or SELL

Return JSON:
{{
    "analysis": "DIRECT ANSWER: [specific answer to question]\\n\\nSYNTHESIS: [balanced analysis of perspectives]",
    "confidence": 0.70,
    "key_points": [
        "Key takeaway 1",
        "Key takeaway 2",
        "Key takeaway 3"
    ],
    "recommendation": "BUY|HOLD|SELL",
    "risk_reward_ratio": "60/40"
}}

Be objective. Answer directly first, then synthesize."""

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

            # Week 13 Day 2: Extract token usage BEFORE parsing (survives JSON errors)
            usage = response.usage
            in_tok = usage.prompt_tokens if usage else 0
            out_tok = usage.completion_tokens if usage else 0

            # Parse JSON response
            content = response.choices[0].message.content

            try:
                data = json.loads(content)
            except json.JSONDecodeError as json_err:
                self.logger.warning(f"{self.__class__.__name__} JSON parse error: {json_err}")
                self.logger.warning(f"Raw content (first 200 chars): {content[:200]}")
                # Fallback: use raw content as analysis, but preserve usage
                data = {
                    "analysis": content,
                    "confidence": 0.5,
                    "key_points": ["Raw response (JSON parse failed)"]
                }

            return AgentResponse(
                role=AgentRole.ARBITER,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                recommendation=data.get("recommendation", "HOLD"),
                input_tokens=in_tok,
                output_tokens=out_tok
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
