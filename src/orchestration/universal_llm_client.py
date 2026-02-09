"""
Universal LLM Client with Provider Fallback.

Week 11 Day 5: Make PLAN node provider-agnostic to unblock Golden Set pipeline.

Supports fallback chain:
1. Anthropic (Claude Sonnet 4.5) - if key available
2. DeepSeek (deepseek-chat) - cost-effective fallback
3. OpenAI (gpt-4o-mini) - secondary fallback
4. Gemini (gemini-2.5-flash) - tertiary fallback

Critical: This unblocks pipeline when Anthropic Console is down.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Import LLM SDKs
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Universal LLM response structure."""
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class UniversalLLMClient:
    """
    Universal LLM client with automatic provider fallback.

    Tries providers in order until one succeeds:
    1. Anthropic (if ANTHROPIC_API_KEY set)
    2. DeepSeek (if DEEPSEEK_API_KEY set)
    3. OpenAI (if OPENAI_API_KEY set)
    4. Gemini (if GOOGLE_API_KEY set)

    Usage:
        client = UniversalLLMClient()
        response = client.generate(system_prompt, user_prompt)
        print(f"Used provider: {response.provider}")
    """

    # Default models for each provider
    DEFAULT_MODELS = {
        "anthropic": "claude-sonnet-4-5-20250929",
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-mini",
        "gemini": "gemini-2.5-flash"
    }

    # Cost per 1M tokens (input/output)
    PRICING = {
        "anthropic": {"input": 3.00, "output": 15.00},
        "deepseek": {"input": 0.14, "output": 0.28},
        "openai": {"input": 0.15, "output": 0.60},
        "gemini": {"input": 0.00, "output": 0.00}  # Free during preview
    }

    def __init__(
        self,
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4000
    ):
        """
        Initialize universal client.

        Args:
            preferred_provider: Preferred provider ("anthropic", "deepseek", "openai", "gemini")
                               If None, tries all in order
            model: Model override (uses default if None)
            temperature: LLM temperature (0.0 = deterministic)
            max_tokens: Maximum output tokens
        """
        self.preferred_provider = preferred_provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Try to initialize providers
        self.available_providers = self._detect_available_providers()

        if not self.available_providers:
            raise ValueError(
                "No LLM providers available! Set at least one API key:\n"
                "- ANTHROPIC_API_KEY\n"
                "- DEEPSEEK_API_KEY\n"
                "- OPENAI_API_KEY\n"
                "- GOOGLE_API_KEY"
            )

        logger.info(f"Available LLM providers: {list(self.available_providers.keys())}")

    def _detect_available_providers(self) -> Dict[str, Any]:
        """
        Detect which providers are available based on API keys.

        Returns:
            Dict of {provider_name: client_instance}
        """
        available = {}

        # Try Anthropic
        if anthropic and os.getenv("ANTHROPIC_API_KEY"):
            try:
                client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                available["anthropic"] = client
                logger.info("✅ Anthropic (Claude) available")
            except Exception as e:
                logger.warning(f"❌ Anthropic init failed: {e}")

        # Try DeepSeek
        if OpenAI and os.getenv("DEEPSEEK_API_KEY"):
            try:
                client = OpenAI(
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url="https://api.deepseek.com"
                )
                available["deepseek"] = client
                logger.info("✅ DeepSeek available")
            except Exception as e:
                logger.warning(f"❌ DeepSeek init failed: {e}")

        # Try OpenAI
        if OpenAI and os.getenv("OPENAI_API_KEY"):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                available["openai"] = client
                logger.info("✅ OpenAI available")
            except Exception as e:
                logger.warning(f"❌ OpenAI init failed: {e}")

        # Try Gemini
        if genai and os.getenv("GOOGLE_API_KEY"):
            try:
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                model_name = self.model if self.model else self.DEFAULT_MODELS["gemini"]
                client = genai.GenerativeModel(model_name)
                available["gemini"] = client
                logger.info("✅ Gemini available")
            except Exception as e:
                logger.warning(f"❌ Gemini init failed: {e}")

        return available

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Generate completion using first available provider.

        Args:
            system_prompt: System instructions
            user_prompt: User query
            json_mode: Request structured JSON output

        Returns:
            LLMResponse with content and metadata

        Raises:
            RuntimeError: If all providers fail
        """
        # Determine provider order
        if self.preferred_provider and self.preferred_provider in self.available_providers:
            providers_to_try = [self.preferred_provider] + [
                p for p in self.available_providers.keys() if p != self.preferred_provider
            ]
        else:
            # Default order: anthropic → deepseek → openai → gemini
            providers_to_try = ["anthropic", "deepseek", "openai", "gemini"]
            providers_to_try = [p for p in providers_to_try if p in self.available_providers]

        errors = []

        for provider in providers_to_try:
            try:
                logger.info(f"Trying provider: {provider}")
                response = self._call_provider(
                    provider,
                    system_prompt,
                    user_prompt,
                    json_mode
                )
                logger.info(f"✅ Success with {provider} ({response.model})")
                return response

            except Exception as e:
                error_msg = f"{provider} failed: {str(e)}"
                logger.warning(f"❌ {error_msg}")
                errors.append(error_msg)
                continue

        # All providers failed
        error_summary = "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(
            f"All LLM providers failed!\n{error_summary}\n\n"
            f"Available providers: {list(self.available_providers.keys())}"
        )

    def _call_provider(
        self,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool
    ) -> LLMResponse:
        """Call specific provider."""

        if provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)

        elif provider == "deepseek":
            return self._call_deepseek(system_prompt, user_prompt, json_mode)

        elif provider == "openai":
            return self._call_openai(system_prompt, user_prompt, json_mode)

        elif provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt)

        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Call Anthropic Claude API."""
        client = self.available_providers["anthropic"]
        model = self.model if self.model else self.DEFAULT_MODELS["anthropic"]

        response = client.messages.create(
            model=model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        content = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Calculate cost
        pricing = self.PRICING["anthropic"]
        cost = (input_tokens / 1_000_000) * pricing["input"] + \
               (output_tokens / 1_000_000) * pricing["output"]

        return LLMResponse(
            content=content,
            provider="anthropic",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )

    def _call_deepseek(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool
    ) -> LLMResponse:
        """Call DeepSeek API (OpenAI-compatible)."""
        client = self.available_providers["deepseek"]
        model = self.model if self.model else self.DEFAULT_MODELS["deepseek"]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Calculate cost
        pricing = self.PRICING["deepseek"]
        cost = (input_tokens / 1_000_000) * pricing["input"] + \
               (output_tokens / 1_000_000) * pricing["output"]

        return LLMResponse(
            content=content,
            provider="deepseek",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )

    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool
    ) -> LLMResponse:
        """Call OpenAI API."""
        client = self.available_providers["openai"]
        model = self.model if self.model else self.DEFAULT_MODELS["openai"]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Calculate cost
        pricing = self.PRICING["openai"]
        cost = (input_tokens / 1_000_000) * pricing["input"] + \
               (output_tokens / 1_000_000) * pricing["output"]

        return LLMResponse(
            content=content,
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Call Google Gemini API."""
        client = self.available_providers["gemini"]
        model = self.model if self.model else self.DEFAULT_MODELS["gemini"]

        # Gemini combines system + user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        response = client.generate_content(full_prompt)
        content = response.text

        # Gemini doesn't provide token counts in free tier
        input_tokens = len(full_prompt) // 4  # Rough estimate
        output_tokens = len(content) // 4

        # Gemini is free during preview
        cost = 0.0

        return LLMResponse(
            content=content,
            provider="gemini",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
