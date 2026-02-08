"""
Unit tests for custom exceptions module.

Week 9 Day 2: Testing Coverage - Exception hierarchy and utility functions.
"""

import pytest
from src.api.exceptions import (
    APEException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    RateLimitError,
    InvalidQueryError,
    OrchestratorError,
    StorageError,
    ExternalServiceError,
    SandboxError,
    TimeoutError,
    ConfigurationError,
    is_retryable,
    get_error_severity
)


class TestAPEException:
    """Tests for base APEException class."""

    def test_default_initialization(self):
        """Test exception with default parameters."""
        exc = APEException(message="Test error")
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.details == {}

    def test_custom_initialization(self):
        """Test exception with custom parameters."""
        exc = APEException(
            message="Custom error",
            status_code=418,
            error_code="CUSTOM_ERROR",
            details={"key": "value"}
        )
        assert exc.message == "Custom error"
        assert exc.status_code == 418
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == {"key": "value"}

    def test_inheritance(self):
        """Test that APEException inherits from Exception."""
        exc = APEException(message="Test")
        assert isinstance(exc, Exception)

    def test_string_representation(self):
        """Test exception string representation."""
        exc = APEException(message="Test error")
        assert str(exc) == "Test error"


# ============================================================================
# Client Errors (4xx)
# ============================================================================

class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = ValidationError(message="Invalid input")
        assert exc.message == "Invalid input"
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details == {}

    def test_with_details(self):
        """Test initialization with details."""
        details = {"field": "email", "reason": "invalid format"}
        exc = ValidationError(message="Validation failed", details=details)
        assert exc.details == details


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_default_message(self):
        """Test default error message."""
        exc = AuthenticationError()
        assert exc.message == "Authentication failed"
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"

    def test_custom_message(self):
        """Test custom error message."""
        exc = AuthenticationError(message="Invalid API key")
        assert exc.message == "Invalid API key"


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_default_message(self):
        """Test default error message."""
        exc = AuthorizationError()
        assert exc.message == "Insufficient permissions"
        assert exc.status_code == 403
        assert exc.error_code == "AUTHORIZATION_ERROR"

    def test_custom_message(self):
        """Test custom error message."""
        exc = AuthorizationError(message="Admin access required")
        assert exc.message == "Admin access required"


class TestResourceNotFoundError:
    """Tests for ResourceNotFoundError."""

    def test_initialization(self):
        """Test resource not found initialization."""
        exc = ResourceNotFoundError(resource="Query", resource_id="123")
        assert exc.message == "Query not found: 123"
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.details == {"resource": "Query", "resource_id": "123"}


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_without_retry_after(self):
        """Test rate limit without retry_after."""
        exc = RateLimitError(message="Too many requests")
        assert exc.message == "Too many requests"
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.details == {}

    def test_with_retry_after(self):
        """Test rate limit with retry_after."""
        exc = RateLimitError(message="Too many requests", retry_after=60)
        assert exc.details == {"retry_after_seconds": 60}


class TestInvalidQueryError:
    """Tests for InvalidQueryError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = InvalidQueryError(message="Query too short")
        assert exc.message == "Query too short"
        assert exc.status_code == 400
        assert exc.error_code == "INVALID_QUERY"

    def test_with_details(self):
        """Test initialization with details."""
        details = {"min_length": 10, "actual_length": 5}
        exc = InvalidQueryError(message="Query too short", details=details)
        assert exc.details == details


# ============================================================================
# Server Errors (5xx)
# ============================================================================

class TestOrchestratorError:
    """Tests for OrchestratorError."""

    def test_without_node(self):
        """Test orchestrator error without node information."""
        exc = OrchestratorError(message="Pipeline failed")
        assert exc.message == "Pipeline failed"
        assert exc.status_code == 500
        assert exc.error_code == "ORCHESTRATOR_ERROR"
        assert exc.details == {}

    def test_with_node(self):
        """Test orchestrator error with node information."""
        exc = OrchestratorError(message="Pipeline failed", node="VEE")
        assert exc.details == {"failed_node": "VEE"}


class TestStorageError:
    """Tests for StorageError."""

    def test_without_storage_type(self):
        """Test storage error without storage type."""
        exc = StorageError(message="Database connection failed")
        assert exc.message == "Database connection failed"
        assert exc.status_code == 500
        assert exc.error_code == "STORAGE_ERROR"
        assert exc.details == {}

    def test_with_storage_type(self):
        """Test storage error with storage type."""
        exc = StorageError(message="Connection failed", storage_type="timescaledb")
        assert exc.details == {"storage_type": "timescaledb"}


class TestExternalServiceError:
    """Tests for ExternalServiceError."""

    def test_default_initialization(self):
        """Test default initialization."""
        exc = ExternalServiceError(service="Anthropic", message="API timeout")
        assert exc.message == "Anthropic error: API timeout"
        assert exc.status_code == 503
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert exc.details == {"service": "Anthropic", "retry_possible": True}

    def test_custom_status_code(self):
        """Test with custom status code."""
        exc = ExternalServiceError(
            service="OpenAI",
            message="Rate limited",
            status_code=429
        )
        assert exc.status_code == 429

    def test_not_retryable(self):
        """Test non-retryable error."""
        exc = ExternalServiceError(
            service="AlphaVantage",
            message="Invalid API key",
            retry_possible=False
        )
        assert exc.details["retry_possible"] is False


class TestSandboxError:
    """Tests for SandboxError."""

    def test_without_code(self):
        """Test sandbox error without code."""
        exc = SandboxError(message="Execution failed")
        assert exc.message == "Execution failed"
        assert exc.status_code == 500
        assert exc.error_code == "SANDBOX_ERROR"
        assert exc.details == {}

    def test_with_code(self):
        """Test sandbox error with code snippet."""
        code = "import pandas as pd; df.head()"
        exc = SandboxError(message="Import error", code=code)
        assert exc.details == {"failed_code": code}


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_initialization(self):
        """Test timeout error initialization."""
        exc = TimeoutError(operation="Query execution", timeout_seconds=30)
        assert exc.message == "Query execution timed out after 30s"
        assert exc.status_code == 504
        assert exc.error_code == "TIMEOUT_ERROR"
        assert exc.details == {
            "operation": "Query execution",
            "timeout_seconds": 30
        }


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_without_config_key(self):
        """Test configuration error without key."""
        exc = ConfigurationError(message="Invalid configuration")
        assert exc.message == "Invalid configuration"
        assert exc.status_code == 500
        assert exc.error_code == "CONFIGURATION_ERROR"
        assert exc.details == {}

    def test_with_config_key(self):
        """Test configuration error with key."""
        exc = ConfigurationError(
            message="Missing required value",
            config_key="ANTHROPIC_API_KEY"
        )
        assert exc.details == {"config_key": "ANTHROPIC_API_KEY"}


# ============================================================================
# Utility Functions
# ============================================================================

class TestIsRetryable:
    """Tests for is_retryable utility function."""

    def test_timeout_error_retryable(self):
        """Test that TimeoutError is retryable."""
        exc = TimeoutError(operation="Query", timeout_seconds=30)
        assert is_retryable(exc) is True

    def test_external_service_error_retryable(self):
        """Test that ExternalServiceError is retryable by default."""
        exc = ExternalServiceError(service="API", message="Timeout")
        assert is_retryable(exc) is True

    def test_external_service_error_not_retryable(self):
        """Test that ExternalServiceError can be marked as not retryable."""
        exc = ExternalServiceError(
            service="API",
            message="Invalid key",
            retry_possible=False
        )
        assert is_retryable(exc) is False

    def test_storage_error_retryable(self):
        """Test that StorageError is retryable."""
        exc = StorageError(message="Connection lost")
        assert is_retryable(exc) is True

    def test_validation_error_not_retryable(self):
        """Test that ValidationError is not retryable."""
        exc = ValidationError(message="Invalid input")
        assert is_retryable(exc) is False

    def test_authentication_error_not_retryable(self):
        """Test that AuthenticationError is not retryable."""
        exc = AuthenticationError()
        assert is_retryable(exc) is False

    def test_authorization_error_not_retryable(self):
        """Test that AuthorizationError is not retryable."""
        exc = AuthorizationError()
        assert is_retryable(exc) is False

    def test_invalid_query_error_not_retryable(self):
        """Test that InvalidQueryError is not retryable."""
        exc = InvalidQueryError(message="Query too short")
        assert is_retryable(exc) is False

    def test_orchestrator_error_not_retryable(self):
        """Test that OrchestratorError is not retryable by default."""
        exc = OrchestratorError(message="Pipeline failed")
        assert is_retryable(exc) is False

    def test_orchestrator_error_with_retry_flag(self):
        """Test OrchestratorError with retry_possible in details."""
        exc = OrchestratorError(message="Transient failure")
        exc.details["retry_possible"] = True
        assert is_retryable(exc) is True

    def test_unknown_exception_not_retryable(self):
        """Test that unknown exceptions are not retryable."""
        exc = ValueError("Some error")
        assert is_retryable(exc) is False


class TestGetErrorSeverity:
    """Tests for get_error_severity utility function."""

    def test_configuration_error_critical(self):
        """Test ConfigurationError has critical severity."""
        exc = ConfigurationError(message="Missing config")
        assert get_error_severity(exc) == "critical"

    def test_storage_error_critical(self):
        """Test StorageError has critical severity."""
        exc = StorageError(message="DB failure")
        assert get_error_severity(exc) == "critical"

    def test_orchestrator_error_critical(self):
        """Test OrchestratorError has critical severity."""
        exc = OrchestratorError(message="Pipeline failed")
        assert get_error_severity(exc) == "critical"

    def test_sandbox_error_error_severity(self):
        """Test SandboxError has error severity."""
        exc = SandboxError(message="Execution failed")
        assert get_error_severity(exc) == "error"

    def test_external_service_error_error_severity(self):
        """Test ExternalServiceError has error severity."""
        exc = ExternalServiceError(service="API", message="Failed")
        assert get_error_severity(exc) == "error"

    def test_timeout_error_error_severity(self):
        """Test TimeoutError has error severity."""
        exc = TimeoutError(operation="Query", timeout_seconds=30)
        assert get_error_severity(exc) == "error"

    def test_rate_limit_error_warning_severity(self):
        """Test RateLimitError has warning severity."""
        exc = RateLimitError(message="Too many requests")
        assert get_error_severity(exc) == "warning"

    def test_validation_error_info_severity(self):
        """Test ValidationError has info severity."""
        exc = ValidationError(message="Invalid input")
        assert get_error_severity(exc) == "info"

    def test_invalid_query_error_info_severity(self):
        """Test InvalidQueryError has info severity."""
        exc = InvalidQueryError(message="Query too short")
        assert get_error_severity(exc) == "info"

    def test_resource_not_found_error_info_severity(self):
        """Test ResourceNotFoundError has info severity."""
        exc = ResourceNotFoundError(resource="Query", resource_id="123")
        assert get_error_severity(exc) == "info"

    def test_authentication_error_default_severity(self):
        """Test AuthenticationError falls back to error severity."""
        exc = AuthenticationError()
        # AuthenticationError не входит ни в одну категорию, должен быть "error"
        assert get_error_severity(exc) == "error"

    def test_unknown_exception_error_severity(self):
        """Test unknown exceptions have error severity."""
        exc = ValueError("Some error")
        assert get_error_severity(exc) == "error"


# ============================================================================
# Integration Tests
# ============================================================================

class TestExceptionIntegration:
    """Integration tests for exception usage patterns."""

    def test_exception_chaining(self):
        """Test that exceptions can be chained properly."""
        try:
            raise ValidationError(message="Inner error")
        except ValidationError as inner:
            outer = OrchestratorError(message="Outer error", node="PLAN")
            assert isinstance(inner, APEException)
            assert isinstance(outer, APEException)

    def test_error_details_serialization(self):
        """Test that error details can be serialized to JSON."""
        import json

        exc = ResourceNotFoundError(resource="Query", resource_id="abc-123")
        details_json = json.dumps(exc.details)
        details = json.loads(details_json)

        assert details["resource"] == "Query"
        assert details["resource_id"] == "abc-123"

    def test_multiple_exception_types(self):
        """Test handling multiple exception types."""
        exceptions = [
            ValidationError(message="Test"),
            AuthenticationError(),
            TimeoutError(operation="Test", timeout_seconds=10),
            ExternalServiceError(service="API", message="Fail")
        ]

        for exc in exceptions:
            assert isinstance(exc, APEException)
            assert hasattr(exc, "message")
            assert hasattr(exc, "status_code")
            assert hasattr(exc, "error_code")
            assert hasattr(exc, "details")
