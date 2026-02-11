"""
Enhanced Multi-Agent Debate Specialists.

Week 13 Day 3: 5 specialized financial analysts for deep analysis.

Specialists:
- EarningsAnalyst: Fundamental analysis (revenue, earnings, growth)
- MarketAnalyst: Technical + macro analysis (charts, trends, economy)
- SentimentAnalyst: News + social media sentiment
- ValuationAnalyst: Fair value assessment (DCF, multiples, comparables)
- RiskAnalyst: Risk management (downside, volatility, tail events)

Each specialist uses different LLM optimized for their domain.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
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

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Data Models
# ============================================================================

class SpecialistRole(str, Enum):
    """Specialist roles in enhanced debate."""
    EARNINGS = "earnings"
    MARKET = "market"
    SENTIMENT = "sentiment"
    VALUATION = "valuation"
    RISK = "risk"


@dataclass
class SpecialistResponse:
    """Response from a specialist."""
    role: SpecialistRole
    analysis: str
    confidence: float  # 0.0-1.0
    key_points: List[str]
    recommendation: Optional[str] = None  # BUY|HOLD|SELL
    warning_flags: Optional[List[str]] = None  # Risk warnings


# ============================================================================
# Base Specialist
# ============================================================================

class BaseSpecialist:
    """Base class for financial specialists."""

    def __init__(self, role: SpecialistRole, provider: str, model: str):
        """
        Initialize specialist.

        Args:
            role: Specialist role
            provider: LLM provider (deepseek/anthropic/openai/gemini)
            model: Model name
        """
        self.role = role
        self.provider = provider
        self.model = model
        self.logger = logging.getLogger(__name__)

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build role-specific prompt."""
        raise NotImplementedError("Subclass must implement build_prompt")

    async def analyze(self, query: str, context: Dict[str, Any]) -> SpecialistResponse:
        """Run analysis from specialist's perspective."""
        raise NotImplementedError("Subclass must implement analyze")


# ============================================================================
# Earnings Analyst (DeepSeek)
# ============================================================================

class EarningsAnalyst(BaseSpecialist):
    """
    Fundamental analyst - focuses on revenue, earnings, growth.

    Provider: DeepSeek (fast & cheap for numerical analysis)
    Focus: Financial statements, growth rates, profitability
    """

    def __init__(self, model: str = "deepseek-chat"):
        """Initialize Earnings analyst with DeepSeek."""
        super().__init__(SpecialistRole.EARNINGS, "deepseek", model)

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment")

        if AsyncOpenAI is None:
            raise ImportError("openai package required")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build earnings analysis prompt."""
        return f"""You are an EARNINGS ANALYST. Focus on fundamental financial analysis.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your expertise:
- Revenue growth and trends
- Earnings quality and sustainability
- Profit margins and efficiency
- Cash flow generation
- Balance sheet strength

Task:
1. Analyze revenue growth trajectory (YoY, QoQ)
2. Assess earnings quality (recurring vs one-time)
3. Evaluate profitability metrics (gross margin, operating margin, net margin)
4. Review cash flow health (operating CF, free CF)
5. Check balance sheet (debt levels, liquidity)

Return JSON:
{{
    "analysis": "Your earnings analysis (2-3 paragraphs)",
    "confidence": 0.75,
    "key_points": [
        "Revenue growth: +XX% YoY",
        "Margin expansion: XX bps",
        "Strong cash generation"
    ],
    "recommendation": "BUY|HOLD|SELL",
    "warning_flags": ["Declining margins", "High debt"] (optional)
}}

Be quantitative. Use specific numbers from financial statements."""

    async def analyze(self, query: str, context: Dict[str, Any]) -> SpecialistResponse:
        """Run earnings analysis."""
        try:
            prompt = self.build_prompt(query, context)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional earnings analyst specializing in fundamental analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # Lower temp for analytical tasks
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return SpecialistResponse(
                role=SpecialistRole.EARNINGS,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                recommendation=data.get("recommendation"),
                warning_flags=data.get("warning_flags")
            )

        except Exception as e:
            self.logger.error(f"Earnings analyst error: {e}", exc_info=True)
            return SpecialistResponse(
                role=SpecialistRole.EARNINGS,
                analysis=f"Error in earnings analysis: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable"],
                recommendation="HOLD"
            )


# ============================================================================
# Market Analyst (GPT-4)
# ============================================================================

class MarketAnalyst(BaseSpecialist):
    """
    Technical + macro analyst.

    Provider: GPT-4 (strong reasoning for market dynamics)
    Focus: Charts, trends, technical indicators, macro environment
    """

    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """Initialize Market analyst with GPT-4."""
        super().__init__(SpecialistRole.MARKET, "openai", model)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        if AsyncOpenAI is None:
            raise ImportError("openai package required")

        self.client = AsyncOpenAI(api_key=api_key)

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build market analysis prompt."""
        return f"""You are a MARKET ANALYST. Focus on technical and macro analysis.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your expertise:
- Technical analysis (trends, support/resistance, indicators)
- Chart patterns (head & shoulders, triangles, breakouts)
- Market microstructure (volume, momentum, volatility)
- Macro environment (Fed policy, rates, economic data)
- Sector rotation and market sentiment

Task:
1. Identify price trend (uptrend/downtrend/sideways)
2. Analyze technical indicators (RSI, MACD, moving averages)
3. Check support/resistance levels
4. Assess volume and momentum
5. Consider macro backdrop (interest rates, inflation, GDP)

Return JSON:
{{
    "analysis": "Your market analysis (2-3 paragraphs)",
    "confidence": 0.70,
    "key_points": [
        "Strong uptrend since XXX",
        "RSI: XX (overbought/neutral/oversold)",
        "Fed policy: supportive/neutral/restrictive"
    ],
    "recommendation": "BUY|HOLD|SELL"
}}

Focus on actionable technical insights."""

    async def analyze(self, query: str, context: Dict[str, Any]) -> SpecialistResponse:
        """Run market analysis."""
        try:
            prompt = self.build_prompt(query, context)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional market analyst specializing in technical and macro analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return SpecialistResponse(
                role=SpecialistRole.MARKET,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                recommendation=data.get("recommendation")
            )

        except Exception as e:
            self.logger.error(f"Market analyst error: {e}", exc_info=True)
            return SpecialistResponse(
                role=SpecialistRole.MARKET,
                analysis=f"Error in market analysis: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable"],
                recommendation="HOLD"
            )


# ============================================================================
# Sentiment Analyst (Gemini)
# ============================================================================

class SentimentAnalyst(BaseSpecialist):
    """
    News + social media sentiment analyst.

    Provider: Gemini (good at text analysis and sentiment)
    Focus: News headlines, analyst ratings, social media buzz
    """

    def __init__(self, model: str = "gemini-pro"):
        """Initialize Sentiment analyst with Gemini."""
        super().__init__(SpecialistRole.SENTIMENT, "gemini", model)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        if genai is None:
            raise ImportError("google-generativeai package required")

        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(model)

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build sentiment analysis prompt."""
        return f"""You are a SENTIMENT ANALYST. Focus on news and market sentiment.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your expertise:
- News sentiment (positive/negative/neutral tone)
- Analyst ratings and price targets
- Social media buzz and retail sentiment
- Media coverage intensity
- Narrative shifts and controversies

Task:
1. Assess recent news sentiment (bullish/bearish/mixed)
2. Review analyst ratings (upgrades/downgrades)
3. Gauge social media sentiment (if available)
4. Identify narrative themes (growth story, turnaround, concerns)
5. Note any controversies or red flags

Return JSON:
{{
    "analysis": "Your sentiment analysis (2-3 paragraphs)",
    "confidence": 0.65,
    "key_points": [
        "News sentiment: positive (XX% positive articles)",
        "Analyst consensus: Buy (XX/XX analysts)",
        "Social buzz: high/medium/low"
    ],
    "recommendation": "BUY|HOLD|SELL",
    "warning_flags": ["Negative news", "Analyst downgrades"]
}}

Focus on sentiment shifts and narrative changes."""

    async def analyze(self, query: str, context: Dict[str, Any]) -> SpecialistResponse:
        """Run sentiment analysis."""
        try:
            prompt = self.build_prompt(query, context)

            # Gemini API call (synchronous, wrap in executor)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model_instance.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=1000
                    )
                )
            )

            # Parse response (Gemini returns text, need to extract JSON)
            content = response.text
            # Try to parse JSON from response
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    raise ValueError("Could not extract JSON from Gemini response")

            return SpecialistResponse(
                role=SpecialistRole.SENTIMENT,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                recommendation=data.get("recommendation"),
                warning_flags=data.get("warning_flags")
            )

        except Exception as e:
            self.logger.error(f"Sentiment analyst error: {e}", exc_info=True)
            return SpecialistResponse(
                role=SpecialistRole.SENTIMENT,
                analysis=f"Error in sentiment analysis: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable"],
                recommendation="HOLD"
            )


# ============================================================================
# Valuation Analyst (Claude)
# ============================================================================

class ValuationAnalyst(BaseSpecialist):
    """
    Fair value analyst.

    Provider: Claude (critical thinking for valuation)
    Focus: DCF, multiples, comparables, intrinsic value
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize Valuation analyst with Claude."""
        super().__init__(SpecialistRole.VALUATION, "anthropic", model)

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        if AsyncAnthropic is None:
            raise ImportError("anthropic package required")

        self.client = AsyncAnthropic(api_key=api_key)

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build valuation analysis prompt."""
        return f"""You are a VALUATION ANALYST. Determine fair value.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your expertise:
- DCF modeling (discount cash flows to present value)
- Multiple-based valuation (P/E, EV/EBITDA, P/S, P/B)
- Comparable company analysis
- Sum-of-the-parts valuation
- Intrinsic value vs market price

Task:
1. Calculate valuation multiples vs peers
2. Assess valuation (cheap/fair/expensive)
3. Estimate fair value range
4. Compare to current price
5. Identify valuation drivers (growth, margins, risk)

Return JSON:
{{
    "analysis": "Your valuation analysis (2-3 paragraphs)",
    "confidence": 0.70,
    "key_points": [
        "P/E: XX vs sector average YY (premium/discount)",
        "Fair value range: $XXX-$YYY",
        "Current price: $ZZZ (overvalued/fairly valued/undervalued)"
    ],
    "recommendation": "BUY|HOLD|SELL"
}}

Be rigorous. Justify fair value with specific multiples."""

    async def analyze(self, query: str, context: Dict[str, Any]) -> SpecialistResponse:
        """Run valuation analysis."""
        try:
            prompt = self.build_prompt(query, context)

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1200,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract JSON from Claude response
            content = response.content[0].text
            data = json.loads(content)

            return SpecialistResponse(
                role=SpecialistRole.VALUATION,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                recommendation=data.get("recommendation")
            )

        except Exception as e:
            self.logger.error(f"Valuation analyst error: {e}", exc_info=True)
            return SpecialistResponse(
                role=SpecialistRole.VALUATION,
                analysis=f"Error in valuation analysis: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable"],
                recommendation="HOLD"
            )


# ============================================================================
# Risk Analyst (GPT-4)
# ============================================================================

class RiskAnalyst(BaseSpecialist):
    """
    Risk management analyst.

    Provider: GPT-4 (conservative reasoning)
    Focus: Downside risks, volatility, tail events, risk/reward
    """

    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """Initialize Risk analyst with GPT-4."""
        super().__init__(SpecialistRole.RISK, "openai", model)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        if AsyncOpenAI is None:
            raise ImportError("openai package required")

        self.client = AsyncOpenAI(api_key=api_key)

    def build_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build risk analysis prompt."""
        return f"""You are a RISK ANALYST. Assess downside risks and risk/reward.

Query: {query}

Context:
{json.dumps(context, indent=2)}

Your expertise:
- Downside risk identification
- Volatility assessment (historical and implied)
- Tail risk and black swan events
- Liquidity risk
- Risk/reward ratio

Task:
1. Identify key downside risks (business, market, regulatory, etc.)
2. Assess volatility (beta, standard deviation)
3. Evaluate liquidity and trading risk
4. Consider tail risks (low probability, high impact)
5. Calculate risk/reward ratio

Return JSON:
{{
    "analysis": "Your risk analysis (2-3 paragraphs)",
    "confidence": 0.75,
    "key_points": [
        "Volatility: XX% (high/medium/low)",
        "Key risks: [list 3-4 major risks]",
        "Risk/reward: XX:1 (favorable/unfavorable)"
    ],
    "recommendation": "BUY|HOLD|SELL",
    "warning_flags": [
        "High volatility",
        "Regulatory risk",
        "Liquidity concerns"
    ]
}}

Be conservative. Err on the side of caution."""

    async def analyze(self, query: str, context: Dict[str, Any]) -> SpecialistResponse:
        """Run risk analysis."""
        try:
            prompt = self.build_prompt(query, context)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional risk analyst with a conservative, safety-first approach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,  # Lower temp for risk assessment
                max_tokens=1200,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return SpecialistResponse(
                role=SpecialistRole.RISK,
                analysis=data.get("analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
                recommendation=data.get("recommendation"),
                warning_flags=data.get("warning_flags")
            )

        except Exception as e:
            self.logger.error(f"Risk analyst error: {e}", exc_info=True)
            return SpecialistResponse(
                role=SpecialistRole.RISK,
                analysis=f"Error in risk analysis: {str(e)}",
                confidence=0.3,
                key_points=["Analysis unavailable"],
                recommendation="HOLD",
                warning_flags=["Analysis error - proceed with caution"]
            )
