"""
LLM-powered Debate for APE 2026.

Week 10 Day 3: Multi-perspective financial analysis using LLMs.

Replaces simple rule-based debate with nuanced LLM-generated perspectives:
- Bull (optimistic)
- Bear (pessimistic)
- Neutral (balanced)
- Synthesis (overall assessment)
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class DebatePerspective:
    """
    Single perspective in a debate.

    Attributes:
        name: Perspective name (Bull/Bear/Neutral)
        analysis: Text analysis from this perspective
        confidence: Confidence score (0.0-1.0)
        supporting_facts: List of facts cited in analysis
    """
    name: str
    analysis: str
    confidence: float
    supporting_facts: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate confidence range."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass
class DebateResult:
    """
    Result of multi-perspective debate.

    Attributes:
        bull_perspective: Optimistic view
        bear_perspective: Pessimistic view
        neutral_perspective: Balanced view
        synthesis: Overall assessment
        confidence: Overall confidence in analysis
    """
    bull_perspective: DebatePerspective
    bear_perspective: DebatePerspective
    neutral_perspective: DebatePerspective
    synthesis: str
    confidence: float

    def __post_init__(self):
        """Validate overall confidence."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")


# ============================================================================
# Prompt Builder
# ============================================================================

class DebatePromptBuilder:
    """
    Builds prompts for LLM debate generation.

    Features:
    - Metric-specific templates
    - Structured output format
    - Citation requirements
    """

    # Prompt templates by metric type
    TEMPLATES = {
        "sharpe_ratio": """Analyze this Sharpe ratio from multiple perspectives:

Ticker: {ticker}
Sharpe Ratio: {value:.4f}
Year: {year}
{supporting_data}

Generate a multi-perspective analysis:

1. **Bull Perspective** (Optimistic):
   - Why is this Sharpe ratio favorable?
   - What does it indicate about risk-adjusted returns?
   - Supporting evidence from the data

2. **Bear Perspective** (Pessimistic):
   - What are the concerns with this metric?
   - What risks or limitations should be considered?
   - Counter-evidence

3. **Neutral Perspective** (Balanced):
   - Objective assessment
   - Context and industry comparison
   - Key takeaways

4. **Synthesis**:
   - Overall assessment integrating all perspectives
   - Confidence level (0-1)
   - Key conclusion

Return as JSON:
{{
  "bull": {{"analysis": "...", "confidence": 0.0-1.0, "facts": ["..."]}},
  "bear": {{"analysis": "...", "confidence": 0.0-1.0, "facts": ["..."]}},
  "neutral": {{"analysis": "...", "confidence": 0.0-1.0, "facts": ["..."]}},
  "synthesis": "...",
  "confidence": 0.0-1.0
}}
""",

        "correlation": """Analyze this correlation from multiple perspectives:

Assets: {ticker1} vs {ticker2}
Correlation: {value:.4f}
Year: {year}
{supporting_data}

Generate multi-perspective analysis (Bull/Bear/Neutral/Synthesis).
Return as JSON with same structure.
""",

        "volatility": """Analyze this volatility from multiple perspectives:

Ticker: {ticker}
Annualized Volatility: {value:.2%}
Year: {year}
{supporting_data}

Generate multi-perspective analysis (Bull/Bear/Neutral/Synthesis).
Return as JSON with same structure.
""",

        "beta": """Analyze this Beta from multiple perspectives:

Ticker: {ticker}
Beta vs {market}: {value:.4f}
Period: {start} to {end}
{supporting_data}

Generate multi-perspective analysis (Bull/Bear/Neutral/Synthesis).
Return as JSON with same structure.
"""
    }

    def build_prompt(self, fact: Dict[str, Any]) -> str:
        """
        Build debate prompt for a financial fact.

        Args:
            fact: Financial fact dict with metric, ticker(s), value, etc.

        Returns:
            Formatted prompt string
        """
        metric = fact.get("metric", "unknown")

        # Get template
        if metric in self.TEMPLATES:
            template = self.TEMPLATES[metric]
        else:
            # Default template
            template = self.TEMPLATES["sharpe_ratio"]

        # Format supporting data
        supporting_data = ""
        if "supporting_data" in fact:
            supporting_data = "Supporting Data:\n" + "\n".join(f"- {d}" for d in fact["supporting_data"])

        # Fill template (remove supporting_data from fact if present to avoid conflict)
        fact_copy = {k: v for k, v in fact.items() if k != "supporting_data"}
        try:
            prompt = template.format(**fact_copy, supporting_data=supporting_data)
        except KeyError as e:
            # Missing key, use generic format
            prompt = f"""Analyze this financial metric from multiple perspectives:

Metric: {metric}
Value: {fact.get('value', 'N/A')}
Data: {fact}

Generate Bull, Bear, Neutral perspectives and Synthesis.
Return as JSON.
"""

        return prompt


# ============================================================================
# LLM Debate Node
# ============================================================================

class LLMDebateNode:
    """
    LLM-powered debate generation.

    Features:
    - Multi-LLM support (OpenAI, Gemini, DeepSeek)
    - Mock provider for testing
    - Structured output parsing
    - Retry logic
    """

    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Initialize debate node.

        Args:
            provider: LLM provider (openai, gemini, deepseek, mock)
            model: Model name (optional, uses default for provider)
        """
        self.provider = provider
        self.model = model
        self.prompt_builder = DebatePromptBuilder()

        # Set default models
        if not self.model:
            defaults = {
                "openai": "gpt-3.5-turbo",
                "gemini": "gemini-1.5-flash",
                "deepseek": "deepseek-chat",
                "mock": "mock",
                "failing_mock": "failing_mock"
            }
            self.model = defaults.get(provider, "gpt-3.5-turbo")

    def generate_debate(self, fact: Dict[str, Any]) -> Optional[DebateResult]:
        """
        Generate multi-perspective debate for a financial fact.

        Args:
            fact: Financial fact dict

        Returns:
            DebateResult or None on failure
        """
        try:
            # Build prompt
            prompt = self.prompt_builder.build_prompt(fact)

            # Call LLM
            if self.provider == "mock":
                response = self._call_mock_llm(fact)
            elif self.provider == "failing_mock":
                return None
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            elif self.provider == "gemini":
                response = self._call_gemini(prompt)
            elif self.provider == "deepseek":
                response = self._call_deepseek(prompt)
            else:
                logger.error(f"Unknown provider: {self.provider}")
                return None

            # Parse response
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Debate generation error: {e}", exc_info=True)
            return None

    def _call_mock_llm(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """Mock LLM call for testing."""
        metric = fact.get("metric", "unknown")
        ticker = fact.get("ticker", fact.get("ticker1", "UNKNOWN"))
        value = fact.get("value", 0.0)

        return {
            "bull": {
                "analysis": f"{ticker}'s {metric} of {value:.4f} indicates strong fundamentals and positive momentum.",
                "confidence": 0.85,
                "facts": [f"{metric}: {value:.4f}", "Above industry average"]
            },
            "bear": {
                "analysis": f"The {metric} of {value:.4f} may not be sustainable given market conditions and potential headwinds.",
                "confidence": 0.75,
                "facts": [f"Market volatility", "Macro uncertainty"]
            },
            "neutral": {
                "analysis": f"{ticker}'s {metric} of {value:.4f} is within normal range for this sector, neither exceptionally strong nor weak.",
                "confidence": 0.90,
                "facts": [f"{metric}: {value:.4f}", "Sector median: similar"]
            },
            "synthesis": f"Overall, {ticker} shows moderate strength with {metric} of {value:.4f}. While bullish factors exist, risks remain. Balanced outlook suggests cautious optimism.",
            "confidence": 0.82
        }

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        # TODO: Implement in Week 10 Day 3 production
        raise NotImplementedError("OpenAI integration pending")

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Google Gemini API."""
        # TODO: Implement in Week 10 Day 3 production
        raise NotImplementedError("Gemini integration pending")

    def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        """Call DeepSeek API."""
        # TODO: Implement in Week 10 Day 3 production
        raise NotImplementedError("DeepSeek integration pending")

    def _parse_response(self, response: Dict[str, Any]) -> DebateResult:
        """
        Parse LLM response into DebateResult.

        Args:
            response: Raw LLM response dict

        Returns:
            DebateResult
        """
        bull = DebatePerspective(
            name="Bull",
            analysis=response["bull"]["analysis"],
            confidence=response["bull"]["confidence"],
            supporting_facts=response["bull"].get("facts", [])
        )

        bear = DebatePerspective(
            name="Bear",
            analysis=response["bear"]["analysis"],
            confidence=response["bear"]["confidence"],
            supporting_facts=response["bear"].get("facts", [])
        )

        neutral = DebatePerspective(
            name="Neutral",
            analysis=response["neutral"]["analysis"],
            confidence=response["neutral"]["confidence"],
            supporting_facts=response["neutral"].get("facts", [])
        )

        return DebateResult(
            bull_perspective=bull,
            bear_perspective=bear,
            neutral_perspective=neutral,
            synthesis=response["synthesis"],
            confidence=response["confidence"]
        )


# ============================================================================
# Debate Validator
# ============================================================================

class DebateValidator:
    """
    Validates LLM-generated debates.

    Checks:
    - All perspectives present
    - Analyses non-empty
    - Confidence scores valid
    - Citations present (warning if missing)
    - Synthesis non-empty
    """

    def validate(self, result: DebateResult) -> bool:
        """
        Validate debate result.

        Args:
            result: DebateResult to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check all perspectives present
            if not result.bull_perspective or not result.bear_perspective or not result.neutral_perspective:
                logger.error("Missing perspective")
                return False

            # Check analyses non-empty
            if not result.bull_perspective.analysis.strip():
                logger.error("Bull analysis is empty")
                return False

            if not result.bear_perspective.analysis.strip():
                logger.error("Bear analysis is empty")
                return False

            if not result.neutral_perspective.analysis.strip():
                logger.error("Neutral analysis is empty")
                return False

            # Check synthesis
            if not result.synthesis.strip():
                logger.error("Synthesis is empty")
                return False

            # Check confidence scores
            if not (0.0 <= result.bull_perspective.confidence <= 1.0):
                logger.error(f"Bull confidence out of range: {result.bull_perspective.confidence}")
                return False

            if not (0.0 <= result.bear_perspective.confidence <= 1.0):
                logger.error(f"Bear confidence out of range: {result.bear_perspective.confidence}")
                return False

            if not (0.0 <= result.neutral_perspective.confidence <= 1.0):
                logger.error(f"Neutral confidence out of range: {result.neutral_perspective.confidence}")
                return False

            if not (0.0 <= result.confidence <= 1.0):
                logger.error(f"Overall confidence out of range: {result.confidence}")
                return False

            # Warn if no citations (not critical)
            total_facts = (
                len(result.bull_perspective.supporting_facts) +
                len(result.bear_perspective.supporting_facts) +
                len(result.neutral_perspective.supporting_facts)
            )

            if total_facts == 0:
                logger.warning("No supporting facts cited in debate")

            return True

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False
