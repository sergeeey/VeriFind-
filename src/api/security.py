"""
Security utilities for APE API.

Week 9 Day 1: Input validation, sanitization, and security checks.
"""

import re
import html
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Optional[str] = None


class InputValidator:
    """
    Input validation and sanitization.

    Protects against:
    - SQL Injection
    - XSS (Cross-Site Scripting)
    - Command Injection
    - Path Traversal
    - Excessive length
    """

    # Dangerous patterns that could indicate injection attacks
    SQL_INJECTION_PATTERNS = [
        r"('|(--)|;|\*|\/\*|\*\/|xp_|sp_|exec|execute|union|select|insert|update|delete|drop|create|alter|grant|revoke)",
        r"(\bor\b|\band\b).*?=.*?",  # SQL boolean conditions
        r"1\s*=\s*1",  # Classic SQL injection test
        r"'\s*or\s*'.*?'\s*=\s*'",  # String-based SQL injection
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, onerror, etc.)
        r"<iframe",  # Iframes
        r"<object",  # Objects
        r"<embed",  # Embeds
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\.\.\/",  # Path traversal
        r"\$\(.*?\)",  # Command substitution
        r"`.*?`",  # Backtick command execution
    ]

    # Safe characters for different contexts
    ALPHANUMERIC_PATTERN = r"^[a-zA-Z0-9\s\-_.,!?]+$"
    QUERY_SAFE_PATTERN = r"^[a-zA-Z0-9\s\-_.,!?:;()\[\]{}\/]+$"

    def __init__(self, max_length: int = 1000):
        """
        Initialize validator.

        Args:
            max_length: Maximum allowed input length
        """
        self.max_length = max_length

    def validate_query(self, query: str) -> ValidationResult:
        """
        Validate user query input.

        Args:
            query: User query text

        Returns:
            ValidationResult with validation status
        """
        # Check length
        if len(query) > self.max_length:
            return ValidationResult(
                is_valid=False,
                error_message=f"Query exceeds maximum length of {self.max_length} characters"
            )

        if len(query.strip()) < 10:
            return ValidationResult(
                is_valid=False,
                error_message="Query must be at least 10 characters"
            )

        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                return ValidationResult(
                    is_valid=False,
                    error_message="Query contains potentially unsafe SQL patterns"
                )

        # Check for XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potential XSS detected: {pattern}")
                return ValidationResult(
                    is_valid=False,
                    error_message="Query contains potentially unsafe script patterns"
                )

        # Check for command injection
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, query):
                logger.warning(f"Potential command injection detected: {pattern}")
                return ValidationResult(
                    is_valid=False,
                    error_message="Query contains potentially unsafe command patterns"
                )

        # Sanitize (escape HTML)
        sanitized = html.escape(query.strip())

        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized
        )

    def validate_api_key(self, api_key: str) -> ValidationResult:
        """
        Validate API key format.

        Args:
            api_key: API key to validate

        Returns:
            ValidationResult
        """
        if not api_key:
            return ValidationResult(
                is_valid=False,
                error_message="API key is required"
            )

        # Check format (should be alphanumeric + underscores/hyphens)
        if not re.match(r"^[a-zA-Z0-9_\-]+$", api_key):
            return ValidationResult(
                is_valid=False,
                error_message="API key contains invalid characters"
            )

        if len(api_key) < 8 or len(api_key) > 128:
            return ValidationResult(
                is_valid=False,
                error_message="API key must be 8-128 characters"
            )

        return ValidationResult(is_valid=True, sanitized_value=api_key)

    def validate_query_id(self, query_id: str) -> ValidationResult:
        """
        Validate query ID format (UUID).

        Args:
            query_id: Query ID to validate

        Returns:
            ValidationResult
        """
        # UUID format: 8-4-4-4-12 hex characters
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

        if not re.match(uuid_pattern, query_id, re.IGNORECASE):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid query ID format"
            )

        return ValidationResult(is_valid=True, sanitized_value=query_id)

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[\\\/\.]{2,}', '', filename)  # Remove ../ and ..\
        sanitized = re.sub(r'[<>:"|?*]', '', sanitized)  # Remove Windows-invalid chars
        sanitized = sanitized.strip()

        return sanitized


class RateLimiter:
    """
    Advanced rate limiter with sliding window.

    Improvements over basic implementation:
    - Per-endpoint rate limits
    - Burst allowance
    - Exponential backoff on violations
    """

    def __init__(self):
        # Store: {key: [(timestamp, endpoint), ...]}
        self.request_log: dict[str, List[Tuple[float, str]]] = {}
        # Store violation counts: {key: count}
        self.violations: dict[str, int] = {}

    def check_rate_limit(
        self,
        key: str,
        endpoint: str,
        limit: int,
        window_seconds: int = 3600,
        burst_limit: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., API key, IP address)
            endpoint: Endpoint being accessed
            limit: Maximum requests per window
            window_seconds: Time window in seconds
            burst_limit: Optional burst limit (short-term spike allowance)

        Returns:
            (is_allowed, error_message)
        """
        import time

        now = time.time()
        window_start = now - window_seconds

        # Initialize if first request
        if key not in self.request_log:
            self.request_log[key] = []

        # Remove old entries
        self.request_log[key] = [
            (ts, ep) for ts, ep in self.request_log[key]
            if ts > window_start
        ]

        # Count requests for this endpoint
        endpoint_requests = [
            ts for ts, ep in self.request_log[key]
            if ep == endpoint
        ]

        # Check burst limit (last 60 seconds)
        if burst_limit:
            burst_window = now - 60
            burst_requests = [ts for ts in endpoint_requests if ts > burst_window]
            if len(burst_requests) >= burst_limit:
                self._record_violation(key)
                return False, f"Burst limit exceeded: {burst_limit} requests/minute"

        # Check window limit
        if len(endpoint_requests) >= limit:
            self._record_violation(key)
            backoff = self._get_backoff_time(key)
            return False, f"Rate limit exceeded: {limit} requests per hour. Try again in {backoff}s"

        # Record this request
        self.request_log[key].append((now, endpoint))

        return True, None

    def _record_violation(self, key: str):
        """Record rate limit violation for exponential backoff."""
        if key not in self.violations:
            self.violations[key] = 0
        self.violations[key] += 1

    def _get_backoff_time(self, key: str) -> int:
        """Calculate exponential backoff time."""
        violations = self.violations.get(key, 0)
        # Exponential: 60s, 120s, 240s, ...
        return min(60 * (2 ** violations), 3600)  # Cap at 1 hour


# Global instances
input_validator = InputValidator(max_length=1000)
rate_limiter = RateLimiter()
