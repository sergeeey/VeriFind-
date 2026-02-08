"""
Custom exceptions for APE API.

Week 9 Day 2: Error handling and categorization.
"""

from typing import Optional, Dict, Any


class APEException(Exception):
    """
    Base exception for APE API.

    All custom exceptions should inherit from this.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize APE exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


# ============================================================================
# Client Errors (4xx)
# ============================================================================

class ValidationError(APEException):
    """Request validation failed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(APEException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(APEException):
    """Authorization failed."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR"
        )


class ResourceNotFoundError(APEException):
    """Requested resource not found."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "resource_id": resource_id}
        )


class RateLimitError(APEException):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class InvalidQueryError(APEException):
    """Query is invalid or malformed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_QUERY",
            details=details
        )


# ============================================================================
# Server Errors (5xx)
# ============================================================================

class OrchestratorError(APEException):
    """Orchestration pipeline failed."""

    def __init__(self, message: str, node: Optional[str] = None):
        details = {}
        if node:
            details["failed_node"] = node

        super().__init__(
            message=message,
            status_code=500,
            error_code="ORCHESTRATOR_ERROR",
            details=details
        )


class StorageError(APEException):
    """Storage operation failed."""

    def __init__(self, message: str, storage_type: Optional[str] = None):
        details = {}
        if storage_type:
            details["storage_type"] = storage_type

        super().__init__(
            message=message,
            status_code=500,
            error_code="STORAGE_ERROR",
            details=details
        )


class ExternalServiceError(APEException):
    """External service call failed."""

    def __init__(
        self,
        service: str,
        message: str,
        status_code: int = 503,
        retry_possible: bool = True
    ):
        super().__init__(
            message=f"{service} error: {message}",
            status_code=status_code,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={
                "service": service,
                "retry_possible": retry_possible
            }
        )


class SandboxError(APEException):
    """Sandbox execution failed."""

    def __init__(self, message: str, code: Optional[str] = None):
        details = {}
        if code:
            details["failed_code"] = code

        super().__init__(
            message=message,
            status_code=500,
            error_code="SANDBOX_ERROR",
            details=details
        )


class TimeoutError(APEException):
    """Operation timed out."""

    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            message=f"{operation} timed out after {timeout_seconds}s",
            status_code=504,
            error_code="TIMEOUT_ERROR",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds
            }
        )


class ConfigurationError(APEException):
    """Configuration is invalid or missing."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key

        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details=details
        )


# ============================================================================
# Utility Functions
# ============================================================================

def is_retryable(exception: Exception) -> bool:
    """
    Check if an exception is retryable.

    Retryable errors:
    - External service errors (network issues, timeouts)
    - Storage errors (transient DB issues)
    - Timeouts

    Non-retryable errors:
    - Validation errors
    - Authentication/Authorization errors
    - Invalid queries
    """
    if isinstance(exception, (TimeoutError, ExternalServiceError, StorageError)):
        return True

    if isinstance(exception, APEException):
        # Check if details indicate retry is possible
        return exception.details.get("retry_possible", False)

    # Unknown exceptions - assume not retryable
    return False


def get_error_severity(exception: Exception) -> str:
    """
    Get error severity level.

    Returns:
        "critical", "error", "warning", or "info"
    """
    if isinstance(exception, (
        ConfigurationError,
        StorageError,
        OrchestratorError
    )):
        return "critical"

    if isinstance(exception, (
        SandboxError,
        ExternalServiceError,
        TimeoutError
    )):
        return "error"

    if isinstance(exception, RateLimitError):
        return "warning"

    if isinstance(exception, (
        ValidationError,
        InvalidQueryError,
        ResourceNotFoundError
    )):
        return "info"

    # Unknown exception
    return "error"
