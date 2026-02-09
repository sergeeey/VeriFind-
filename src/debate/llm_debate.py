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

# LLM Provider SDKs
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import OpenAI as DeepSeekClient  # DeepSeek uses OpenAI-compatible API
except ImportError:
    DeepSeekClient = None

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

    @property
    def key_points(self) -> List[str]:
        """Alias for supporting_facts (for backward compatibility with real_llm_adapter)."""
        return self.supporting_facts


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
                "openai": "gpt-4o-mini",  # Cheap and fast ($0.15 input/$0.60 output per 1M tokens)
                "gemini": "gemini-2.5-flash",  # Latest stable Gemini model
                "deepseek": "deepseek-chat",
                "mock": "mock",
                "failing_mock": "failing_mock"
            }
            self.model = defaults.get(provider, "gpt-4o-mini")

        # Cost tracking statistics
        self.stats = {
            "total_calls": 0,
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "by_provider": {}
        }

        # Initialize API clients
        self._init_clients()

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

    def _init_clients(self):
        """Initialize API clients for providers."""
        if self.provider == "openai":
            if OpenAI is None:
                raise ImportError("openai package not installed. Run: pip install openai")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.client = OpenAI(api_key=api_key)

        elif self.provider == "gemini":
            if genai is None:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)

        elif self.provider == "deepseek":
            if DeepSeekClient is None:
                raise ImportError("openai package not installed. Run: pip install openai")
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not found in environment")
            # DeepSeek uses OpenAI-compatible API
            self.client = DeepSeekClient(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

        elif self.provider in ["mock", "failing_mock"]:
            self.client = None  # No client needed for mock

    def get_stats(self) -> Dict[str, Any]:
        """Get cost tracking statistics."""
        return self.stats.copy()

    def _reset_stats(self):
        """Reset statistics (for testing)."""
        self.stats = {
            "total_calls": 0,
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "by_provider": {}
        }

    def _update_stats(self, input_tokens: int, output_tokens: int, cost: float):
        """Update cost tracking statistics."""
        self.stats["total_calls"] += 1
        self.stats["total_input_tokens"] += input_tokens
        self.stats["total_output_tokens"] += output_tokens
        self.stats["total_cost"] += cost

        # Track by provider
        if self.provider not in self.stats["by_provider"]:
            self.stats["by_provider"][self.provider] = {
                "calls": 0,
                "cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0
            }

        provider_stats = self.stats["by_provider"][self.provider]
        provider_stats["calls"] += 1
        provider_stats["cost"] += cost
        provider_stats["input_tokens"] += input_tokens
        provider_stats["output_tokens"] += output_tokens

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
        """
        Call OpenAI API.

        Uses structured output (JSON mode) for reliable debate parsing.

        Pricing (gpt-4o-mini):
        - Input: $0.15 per 1M tokens
        - Output: $0.60 per 1M tokens
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst providing multi-perspective analysis. "
                                   "Respond ONLY with valid JSON matching this schema: "
                                   '{"bull": {"analysis": "...", "confidence": 0.8, "facts": ["..."]}, '
                                   '"bear": {"analysis": "...", "confidence": 0.7, "facts": ["..."]}, '
                                   '"neutral": {"analysis": "...", "confidence": 0.9, "facts": ["..."]}, '
                                   '"synthesis": "...", "confidence": 0.8}'
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )

            # Extract JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            # gpt-4o-mini pricing
            input_cost = (input_tokens / 1_000_000) * 0.15
            output_cost = (output_tokens / 1_000_000) * 0.60
            total_cost = input_cost + output_cost

            # Update stats
            self._update_stats(input_tokens, output_tokens, total_cost)

            logger.info(f"OpenAI debate generated: {input_tokens} in + {output_tokens} out, ${total_cost:.6f}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """
        Call Google Gemini API.

        Uses JSON mode for structured output.

        Pricing (gemini-2.0-flash-exp - FREE during preview):
        - Input: $0.00 per 1M tokens
        - Output: $0.00 per 1M tokens
        """
        try:
            # Configure generation
            generation_config = {
                "temperature": 0.7,
                "max_output_tokens": 2000,
                "response_mime_type": "application/json",
            }

            system_instruction = """You are a financial analyst providing multi-perspective analysis.
Respond ONLY with valid JSON matching this schema:
{
  "bull": {"analysis": "...", "confidence": 0.8, "facts": ["..."]},
  "bear": {"analysis": "...", "confidence": 0.7, "facts": ["..."]},
  "neutral": {"analysis": "...", "confidence": 0.9, "facts": ["..."]},
  "synthesis": "...",
  "confidence": 0.8
}"""

            # Create model with system instruction
            model = genai.GenerativeModel(
                self.model,
                generation_config=generation_config,
                system_instruction=system_instruction
            )

            # Generate response
            response = model.generate_content(prompt)

            # Extract JSON
            content = response.text
            result = json.loads(content)

            # Calculate token usage and cost
            # Gemini 2.0 Flash is free during preview, but track tokens anyway
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count

            # Free during preview
            total_cost = 0.0

            # Update stats
            self._update_stats(input_tokens, output_tokens, total_cost)

            logger.info(f"Gemini debate generated: {input_tokens} in + {output_tokens} out, ${total_cost:.6f}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise

    def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        """
        Call DeepSeek API.

        Uses OpenAI-compatible API with JSON mode.

        Pricing (deepseek-chat):
        - Input: $0.14 per 1M tokens (cache miss)
        - Output: $0.28 per 1M tokens
        - Cache hit: $0.014 per 1M tokens (90% discount)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst providing multi-perspective analysis. "
                                   "Respond ONLY with valid JSON matching this schema: "
                                   '{"bull": {"analysis": "...", "confidence": 0.8, "facts": ["..."]}, '
                                   '"bear": {"analysis": "...", "confidence": 0.7, "facts": ["..."]}, '
                                   '"neutral": {"analysis": "...", "confidence": 0.9, "facts": ["..."]}, '
                                   '"synthesis": "...", "confidence": 0.8}'
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )

            # Extract JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            # DeepSeek pricing (assuming no cache for first call)
            input_cost = (input_tokens / 1_000_000) * 0.14
            output_cost = (output_tokens / 1_000_000) * 0.28
            total_cost = input_cost + output_cost

            # Update stats
            self._update_stats(input_tokens, output_tokens, total_cost)

            logger.info(f"DeepSeek debate generated: {input_tokens} in + {output_tokens} out, ${total_cost:.6f}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse DeepSeek JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}", exc_info=True)
            raise

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
