"""
Unit tests for security module.

Week 9 Day 2: Testing Coverage - Security validation and rate limiting.
"""

import pytest
from src.api.security import InputValidator, RateLimiter, ValidationResult


class TestInputValidator:
    """Tests for InputValidator class."""

    def setup_method(self):
        """Setup test instance."""
        self.validator = InputValidator(max_length=1000)

    # ========================================================================
    # Query Validation Tests
    # ========================================================================

    def test_valid_query(self):
        """Test valid query passes validation."""
        result = self.validator.validate_query("Calculate the Sharpe ratio of SPY for 2023")
        assert result.is_valid is True
        assert result.error_message is None
        assert result.sanitized_value is not None

    def test_query_too_short(self):
        """Test query too short fails validation."""
        result = self.validator.validate_query("short")
        assert result.is_valid is False
        assert "at least 10 characters" in result.error_message

    def test_query_too_long(self):
        """Test query exceeding max length fails validation."""
        long_query = "a" * 1001
        result = self.validator.validate_query(long_query)
        assert result.is_valid is False
        assert "exceeds maximum length" in result.error_message

    # ========================================================================
    # SQL Injection Tests
    # ========================================================================

    def test_sql_injection_select(self):
        """Test SQL SELECT injection is blocked."""
        result = self.validator.validate_query(
            "Calculate returns; SELECT * FROM users WHERE 1=1"
        )
        assert result.is_valid is False
        assert "unsafe SQL patterns" in result.error_message

    def test_sql_injection_union(self):
        """Test SQL UNION injection is blocked."""
        result = self.validator.validate_query(
            "Show data UNION SELECT password FROM users"
        )
        assert result.is_valid is False
        assert "unsafe SQL patterns" in result.error_message

    def test_sql_injection_boolean(self):
        """Test SQL boolean injection is blocked."""
        result = self.validator.validate_query(
            "Get data WHERE 1=1 OR 1=1"
        )
        assert result.is_valid is False
        assert "unsafe SQL patterns" in result.error_message

    def test_sql_injection_comment(self):
        """Test SQL comment injection is blocked."""
        result = self.validator.validate_query(
            "Calculate returns-- DROP TABLE users"
        )
        assert result.is_valid is False
        assert "unsafe SQL patterns" in result.error_message

    # ========================================================================
    # XSS Tests
    # ========================================================================

    def test_xss_script_tag(self):
        """Test XSS script tag is blocked."""
        result = self.validator.validate_query(
            "Calculate <script>alert('xss')</script> returns"
        )
        assert result.is_valid is False
        assert "unsafe script patterns" in result.error_message

    def test_xss_javascript_protocol(self):
        """Test XSS javascript: protocol is blocked."""
        result = self.validator.validate_query(
            "Show data javascript:alert('xss')"
        )
        assert result.is_valid is False
        assert "unsafe script patterns" in result.error_message

    def test_xss_event_handler(self):
        """Test XSS event handler is blocked."""
        result = self.validator.validate_query(
            "Calculate <img src=x onerror=alert(1)> returns"
        )
        assert result.is_valid is False
        assert "unsafe script patterns" in result.error_message

    def test_xss_iframe(self):
        """Test XSS iframe is blocked."""
        result = self.validator.validate_query(
            "Show <iframe src='evil.com'></iframe> data"
        )
        assert result.is_valid is False
        assert "unsafe script patterns" in result.error_message

    # ========================================================================
    # Command Injection Tests
    # ========================================================================

    def test_command_injection_semicolon(self):
        """Test command injection with semicolon is blocked."""
        result = self.validator.validate_query(
            "Calculate returns; rm -rf /"
        )
        assert result.is_valid is False
        assert "unsafe command patterns" in result.error_message

    def test_command_injection_pipe(self):
        """Test command injection with pipe is blocked."""
        result = self.validator.validate_query(
            "Show data | cat /etc/passwd"
        )
        assert result.is_valid is False
        assert "unsafe command patterns" in result.error_message

    def test_command_injection_substitution(self):
        """Test command substitution is blocked."""
        result = self.validator.validate_query(
            "Calculate $(whoami) returns"
        )
        assert result.is_valid is False
        assert "unsafe command patterns" in result.error_message

    def test_command_injection_backtick(self):
        """Test backtick command execution is blocked."""
        result = self.validator.validate_query(
            "Show `ls -la` data"
        )
        assert result.is_valid is False
        assert "unsafe command patterns" in result.error_message

    # ========================================================================
    # Sanitization Tests
    # ========================================================================

    def test_html_escaping(self):
        """Test HTML special characters are escaped."""
        result = self.validator.validate_query(
            "Calculate returns for <ticker> & <other>"
        )
        assert result.is_valid is True
        assert "&lt;" in result.sanitized_value
        assert "&gt;" in result.sanitized_value
        assert "&amp;" in result.sanitized_value

    # ========================================================================
    # API Key Validation Tests
    # ========================================================================

    def test_valid_api_key(self):
        """Test valid API key passes validation."""
        result = self.validator.validate_api_key("dev_key_12345")
        assert result.is_valid is True

    def test_empty_api_key(self):
        """Test empty API key fails validation."""
        result = self.validator.validate_api_key("")
        assert result.is_valid is False
        assert "required" in result.error_message

    def test_api_key_invalid_characters(self):
        """Test API key with invalid characters fails validation."""
        result = self.validator.validate_api_key("key with spaces!")
        assert result.is_valid is False
        assert "invalid characters" in result.error_message

    def test_api_key_too_short(self):
        """Test API key too short fails validation."""
        result = self.validator.validate_api_key("short")
        assert result.is_valid is False
        assert "8-128 characters" in result.error_message

    def test_api_key_too_long(self):
        """Test API key too long fails validation."""
        long_key = "a" * 129
        result = self.validator.validate_api_key(long_key)
        assert result.is_valid is False
        assert "8-128 characters" in result.error_message

    # ========================================================================
    # Query ID Validation Tests
    # ========================================================================

    def test_valid_uuid(self):
        """Test valid UUID passes validation."""
        result = self.validator.validate_query_id("550e8400-e29b-41d4-a716-446655440000")
        assert result.is_valid is True

    def test_invalid_uuid_format(self):
        """Test invalid UUID format fails validation."""
        result = self.validator.validate_query_id("not-a-uuid")
        assert result.is_valid is False
        assert "Invalid query ID format" in result.error_message

    # ========================================================================
    # Filename Sanitization Tests
    # ========================================================================

    def test_sanitize_filename_path_traversal(self):
        """Test path traversal is removed from filename."""
        sanitized = self.validator.sanitize_filename("../../etc/passwd")
        assert ".." not in sanitized
        assert "/" not in sanitized

    def test_sanitize_filename_windows_invalid(self):
        """Test Windows invalid characters are removed."""
        sanitized = self.validator.sanitize_filename("file<>:\"|?*.txt")
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def setup_method(self):
        """Setup test instance."""
        self.limiter = RateLimiter()

    def test_first_request_allowed(self):
        """Test first request is always allowed."""
        is_allowed, error = self.limiter.check_rate_limit(
            key="test_key",
            endpoint="test",
            limit=10,
            window_seconds=60
        )
        assert is_allowed is True
        assert error is None

    def test_within_limit(self):
        """Test requests within limit are allowed."""
        for i in range(5):
            is_allowed, error = self.limiter.check_rate_limit(
                key="test_key",
                endpoint="test",
                limit=10,
                window_seconds=60
            )
            assert is_allowed is True

    def test_exceed_limit(self):
        """Test exceeding limit is blocked."""
        # Make 10 requests (limit)
        for i in range(10):
            self.limiter.check_rate_limit(
                key="test_key",
                endpoint="test",
                limit=10,
                window_seconds=60
            )

        # 11th request should be blocked
        is_allowed, error = self.limiter.check_rate_limit(
            key="test_key",
            endpoint="test",
            limit=10,
            window_seconds=60
        )
        assert is_allowed is False
        assert "Rate limit exceeded" in error

    def test_burst_limit(self):
        """Test burst limit protection."""
        # Make requests exceeding burst limit
        for i in range(5):
            self.limiter.check_rate_limit(
                key="test_key",
                endpoint="test",
                limit=100,
                window_seconds=3600,
                burst_limit=3
            )

        # Should be blocked by burst limit
        is_allowed, error = self.limiter.check_rate_limit(
            key="test_key",
            endpoint="test",
            limit=100,
            window_seconds=3600,
            burst_limit=3
        )
        assert is_allowed is False
        assert "Burst limit exceeded" in error

    def test_different_endpoints_separate_limits(self):
        """Test different endpoints have separate rate limits."""
        # Exhaust limit on endpoint1
        for i in range(5):
            self.limiter.check_rate_limit(
                key="test_key",
                endpoint="endpoint1",
                limit=5,
                window_seconds=60
            )

        # endpoint2 should still be available
        is_allowed, error = self.limiter.check_rate_limit(
            key="test_key",
            endpoint="endpoint2",
            limit=5,
            window_seconds=60
        )
        assert is_allowed is True

    def test_exponential_backoff(self):
        """Test exponential backoff on violations."""
        # Trigger multiple violations
        for i in range(15):
            self.limiter.check_rate_limit(
                key="test_key",
                endpoint="test",
                limit=5,
                window_seconds=60
            )

        # Check backoff time increases
        backoff1 = self.limiter._get_backoff_time("test_key")
        assert backoff1 > 0

        # Trigger more violations
        for i in range(5):
            self.limiter.check_rate_limit(
                key="test_key",
                endpoint="test",
                limit=5,
                window_seconds=60
            )

        backoff2 = self.limiter._get_backoff_time("test_key")
        assert backoff2 > backoff1

    def test_backoff_cap(self):
        """Test backoff time is capped at 1 hour."""
        # Trigger many violations
        for i in range(100):
            self.limiter.check_rate_limit(
                key="test_key",
                endpoint="test",
                limit=1,
                window_seconds=60
            )

        backoff = self.limiter._get_backoff_time("test_key")
        assert backoff <= 3600  # 1 hour cap
