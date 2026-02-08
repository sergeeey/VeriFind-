"""
Claude API Client with retry logic and rate limiting.

Week 1 Day 3: Anthropic SDK integration
"""

import os
import time
import json
from typing import Optional, Dict, Any, Type
from datetime import datetime, timedelta, UTC

import anthropic
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, requests_per_day: int = 1000):
        self.requests_per_day = requests_per_day
        self.requests_today = 0
        self.current_date = datetime.now(UTC).date()

    def check_and_increment(self) -> bool:
        """
        Check if request is allowed and increment counter.

        Returns:
            True if request allowed, False otherwise
        """
        today = datetime.now(UTC).date()

        # Reset counter if new day
        if today > self.current_date:
            self.requests_today = 0
            self.current_date = today

        if self.requests_today >= self.requests_per_day:
            return False

        self.requests_today += 1
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return {
            "requests_today": self.requests_today,
            "limit": self.requests_per_day,
            "remaining": max(0, self.requests_per_day - self.requests_today),
            "resets_at": datetime.combine(
                self.current_date + timedelta(days=1),
                datetime.min.time()
            ).isoformat()
        }


class ClaudeClient:
    """
    Claude API client for PLAN node.

    Features:
    - Structured output generation (Pydantic)
    - Automatic retry with exponential backoff
    - Rate limiting (1000 req/day default)
    - Error handling and logging
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_retries: int = 3,
        requests_per_day: int = 1000
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_retries: Maximum retry attempts
            requests_per_day: Daily rate limit
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment or parameters"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries

        # Rate limiting
        self.rate_limiter = RateLimiter(requests_per_day)

        # Stats
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError
        ))
    )
    def _make_request(
        self,
        messages: list,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0
    ) -> str:
        """
        Make API request with retry logic.

        Args:
            messages: Conversation messages
            system: System prompt
            max_tokens: Maximum response tokens
            temperature: Sampling temperature

        Returns:
            Response text

        Raises:
            anthropic.APIError: On API errors
            RateLimitError: If rate limit exceeded
        """
        # Check rate limit
        if not self.rate_limiter.check_and_increment():
            status = self.rate_limiter.get_status()
            raise anthropic.RateLimitError(
                f"Daily rate limit exceeded. Resets at {status['resets_at']}"
            )

        self.stats["total_requests"] += 1

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages
            )

            self.stats["successful_requests"] += 1
            return response.content[0].text

        except Exception as e:
            self.stats["failed_requests"] += 1
            self.stats["retries"] += 1
            raise

    def generate_structured_output(
        self,
        prompt: str,
        output_schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        validation_retries: int = 2
    ) -> BaseModel:
        """
        Generate structured output conforming to Pydantic schema.

        Args:
            prompt: User prompt
            output_schema: Pydantic model class
            system_prompt: System prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            validation_retries: Number of retries on validation failure

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError: If response doesn't match schema after retries
        """
        # Build system prompt with schema
        schema_json = output_schema.schema_json(indent=2)

        full_system = f"""You are a financial analysis planning assistant.

Generate a valid JSON response that EXACTLY matches this Pydantic schema:

{schema_json}

CRITICAL RULES:
1. Response must be valid JSON
2. All required fields must be present
3. Field types must match exactly
4. No extra fields outside schema
5. Use proper escaping for strings

Return ONLY the JSON object, no explanation."""

        if system_prompt:
            full_system = f"{system_prompt}\n\n{full_system}"

        messages = [{"role": "user", "content": prompt}]

        # Try up to validation_retries times
        last_error = None
        for attempt in range(validation_retries + 1):
            try:
                # Get response
                response_text = self._make_request(
                    messages=messages,
                    system=full_system,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                # Extract JSON (handle markdown code blocks)
                json_text = self._extract_json(response_text)

                # Parse and validate
                data = json.loads(json_text)
                validated = output_schema(**data)

                return validated

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e

                if attempt < validation_retries:
                    # Add feedback for retry
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": f"""The response was invalid. Error: {str(e)}

Please try again with a valid JSON response matching the schema exactly."""
                    })
                    continue
                else:
                    # Final attempt failed
                    raise ValidationError(
                        f"Failed to generate valid response after {validation_retries + 1} attempts. "
                        f"Last error: {str(last_error)}"
                    )

        raise RuntimeError("Unreachable code")

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from response (handles markdown code blocks).

        Args:
            text: Response text

        Returns:
            Extracted JSON string
        """
        # Remove markdown code blocks
        text = text.strip()

        if text.startswith("```"):
            # Find first ```json or ``` block
            lines = text.split("\n")
            start_idx = 0
            end_idx = len(lines)

            for i, line in enumerate(lines):
                if line.startswith("```"):
                    if start_idx == 0:
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break

            text = "\n".join(lines[start_idx:end_idx])

        return text.strip()

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            **self.stats,
            "rate_limit": self.rate_limiter.get_status(),
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0.0
            )
        }
