"""
DeepSeek R1 Adapter for DSPy.

Week 5 Day 4: Enable DSPy optimization with DeepSeek R1 API.

DeepSeek API is OpenAI-compatible, so we use dspy.LM with custom base_url.
"""

import os
import dspy
from typing import Optional


class DeepSeekR1:
    """
    DeepSeek R1 model adapter for DSPy.

    Uses OpenAI-compatible API with custom base URL via dspy.LM.

    Usage:
        lm = DeepSeekR1(
            model='deepseek-reasoner',
            api_key=os.getenv('DEEPSEEK_API_KEY')
        )
        dspy.settings.configure(lm=lm.lm)
    """

    def __init__(
        self,
        model: str = 'deepseek-reasoner',
        api_key: Optional[str] = None,
        api_base: str = 'https://api.deepseek.com',
        **kwargs
    ):
        """
        Initialize DeepSeek R1 adapter.

        Args:
            model: DeepSeek model name (default: deepseek-reasoner)
            api_key: DeepSeek API key (defaults to DEEPSEEK_API_KEY env var)
            api_base: API base URL (default: https://api.deepseek.com)
            **kwargs: Additional arguments
        """
        # Get API key from env if not provided
        if api_key is None:
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                raise ValueError(
                    "DeepSeek API key not found. "
                    "Set DEEPSEEK_API_KEY environment variable or pass api_key parameter."
                )

        self.model = model
        self.api_key = api_key
        self.api_base = api_base

        # Create dspy.LM with OpenAI-compatible settings
        # DSPy 3.x uses dspy.LM(model="provider/model-name")
        self.lm = dspy.LM(
            model=f'openai/{model}',  # Use openai provider with custom model
            api_key=api_key,
            api_base=api_base,
            **kwargs
        )

    def __repr__(self):
        return f"DeepSeekR1(model={self.model})"


def configure_deepseek(
    model: str = 'deepseek-reasoner',
    api_key: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 4000
) -> DeepSeekR1:
    """
    Configure DSPy to use DeepSeek R1.

    Args:
        model: DeepSeek model name
        api_key: API key (optional, reads from env)
        temperature: Sampling temperature (0.0 for deterministic)
        max_tokens: Maximum tokens in response

    Returns:
        Configured DeepSeekR1 instance

    Example:
        >>> from src.optimization.deepseek_adapter import configure_deepseek
        >>> deepseek = configure_deepseek()
        >>> # LM is already configured globally via dspy.settings
    """
    deepseek = DeepSeekR1(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens
    )

    # Configure DSPy globally with the LM instance
    dspy.settings.configure(lm=deepseek.lm)

    return deepseek


# Pricing info for reference
DEEPSEEK_PRICING = {
    'deepseek-reasoner': {
        'input': 0.55,   # $ per 1M tokens
        'output': 2.19,  # $ per 1M tokens
        'cache_hit': 0.14  # $ per 1M cached tokens (90% discount)
    },
    'deepseek-chat': {
        'input': 0.27,
        'output': 1.10,
        'cache_hit': 0.027
    }
}


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = 'deepseek-reasoner',
    cache_hits: int = 0
) -> float:
    """
    Estimate cost of DeepSeek API call.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name
        cache_hits: Number of cached input tokens

    Returns:
        Estimated cost in USD
    """
    pricing = DEEPSEEK_PRICING.get(model, DEEPSEEK_PRICING['deepseek-reasoner'])

    # Calculate costs
    input_cost = (input_tokens - cache_hits) * pricing['input'] / 1_000_000
    output_cost = output_tokens * pricing['output'] / 1_000_000
    cache_cost = cache_hits * pricing['cache_hit'] / 1_000_000

    total_cost = input_cost + output_cost + cache_cost
    return total_cost
