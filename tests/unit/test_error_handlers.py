"""
Unit tests for error handlers module.

Week 9 Day 2: Testing Coverage - Exception handlers and middleware.
"""

import pytest
import json
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.api.error_handlers import (
    ErrorResponse,
    ape_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    request_id_middleware,
    error_logging_middleware,
    configure_logging
)
from src.api.exceptions import (
    ValidationError as APEValidationError,
    AuthenticationError,
    RateLimitError,
    OrchestratorError,
    TimeoutError
)


# ============================================================================
# ErrorResponse Tests
# ============================================================================

class TestErrorResponse:
    """Tests for ErrorResponse class."""

    def test_create_minimal(self):
        """Test creating error response with minimal parameters."""
        response = ErrorResponse.create(
            status_code=400,
            error_code="BAD_REQUEST",
            message="Invalid request"
        )

        assert response["error"]["code"] == "BAD_REQUEST"
        assert response["error"]["message"] == "Invalid request"
        assert response["error"]["status"] == 400
        assert "timestamp" in response["error"]

    def test_create_with_details(self):
        """Test creating error response with details."""
        details = {"field": "email", "reason": "invalid"}
        response = ErrorResponse.create(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            details=details
        )

        assert response["error"]["details"] == details

    def test_create_with_request_id(self):
        """Test creating error response with request ID."""
        response = ErrorResponse.create(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="Server error",
            request_id="req-123"
        )

        assert response["error"]["request_id"] == "req-123"

    def test_create_with_path(self):
        """Test creating error response with path."""
        response = ErrorResponse.create(
            status_code=404,
            error_code="NOT_FOUND",
            message="Resource not found",
            path="/api/query/123"
        )

        assert response["error"]["path"] == "/api/query/123"

    def test_timestamp_format(self):
        """Test timestamp is in ISO format with Z suffix."""
        response = ErrorResponse.create(
            status_code=500,
            error_code="ERROR",
            message="Test"
        )

        timestamp = response["error"]["timestamp"]
        assert timestamp.endswith("Z")
        # Verify it can be parsed as ISO datetime
        datetime.fromisoformat(timestamp.rstrip("Z"))


# ============================================================================
# Exception Handler Tests
# ============================================================================

class TestAPEExceptionHandler:
    """Tests for ape_exception_handler."""

    @pytest.mark.asyncio
    async def test_handle_validation_error(self):
        """Test handling ValidationError."""
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/query"
        request.state.request_id = "req-123"

        # Create exception
        exc = APEValidationError(
            message="Invalid input",
            details={"field": "query"}
        )

        # Handle exception
        response = await ape_exception_handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

        content = json.loads(response.body.decode())
        assert content["error"]["code"] == "VALIDATION_ERROR"
        assert content["error"]["message"] == "Invalid input"
        assert content["error"]["details"] == {"field": "query"}
        assert content["error"]["request_id"] == "req-123"

    @pytest.mark.asyncio
    async def test_handle_authentication_error(self):
        """Test handling AuthenticationError."""
        request = Mock(spec=Request)
        request.url.path = "/api/query"
        request.state.request_id = "req-456"

        exc = AuthenticationError()

        response = await ape_exception_handler(request, exc)

        assert response.status_code == 401
        content = json.loads(response.body.decode())
        assert content["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self):
        """Test handling RateLimitError."""
        request = Mock(spec=Request)
        request.url.path = "/api/query"
        request.state.request_id = "req-789"

        exc = RateLimitError(message="Too many requests", retry_after=60)

        response = await ape_exception_handler(request, exc)

        assert response.status_code == 429
        content = json.loads(response.body.decode())
        assert content["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert content["error"]["details"]["retry_after_seconds"] == 60

    @pytest.mark.asyncio
    async def test_handle_timeout_error(self):
        """Test handling TimeoutError."""
        request = Mock(spec=Request)
        request.url.path = "/api/query/execute"
        request.state.request_id = "req-timeout"

        exc = TimeoutError(operation="Query execution", timeout_seconds=30)

        response = await ape_exception_handler(request, exc)

        assert response.status_code == 504
        content = json.loads(response.body.decode())
        assert content["error"]["code"] == "TIMEOUT_ERROR"
        assert "30s" in content["error"]["message"]

    @pytest.mark.asyncio
    async def test_logging_with_severity(self, caplog):
        """Test that errors are logged with appropriate severity."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "req-log"

        with caplog.at_level(logging.CRITICAL):
            exc = OrchestratorError(message="Critical failure")
            await ape_exception_handler(request, exc)

        # OrchestratorError should be logged as CRITICAL
        assert any("ORCHESTRATOR_ERROR" in record.message for record in caplog.records)


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler."""

    @pytest.mark.asyncio
    async def test_handle_request_validation_error(self):
        """Test handling FastAPI RequestValidationError."""
        request = Mock(spec=Request)
        request.url.path = "/api/query"
        request.state.request_id = "req-validation"

        # Create mock validation error
        from pydantic_core import ValidationError as PydanticCoreValidationError

        # Mock the validation error structure
        exc = Mock(spec=RequestValidationError)
        exc.errors = Mock(return_value=[
            {
                "loc": ("body", "query"),
                "msg": "field required",
                "type": "value_error.missing"
            },
            {
                "loc": ("body", "priority"),
                "msg": "value is not a valid enumeration member",
                "type": "type_error.enum"
            }
        ])

        response = await validation_exception_handler(request, exc)

        assert response.status_code == 422
        content = json.loads(response.body.decode())

        assert content["error"]["code"] == "VALIDATION_ERROR"
        assert content["error"]["message"] == "Request validation failed"

        errors = content["error"]["details"]["validation_errors"]
        assert len(errors) == 2
        assert errors[0]["field"] == "body.query"
        assert errors[0]["message"] == "field required"

    @pytest.mark.asyncio
    async def test_validation_error_logging(self, caplog):
        """Test that validation errors are logged as warnings."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "req-log"

        exc = Mock(spec=RequestValidationError)
        exc.errors = Mock(return_value=[
            {"loc": ("body", "query"), "msg": "required", "type": "missing"}
        ])

        with caplog.at_level(logging.WARNING):
            await validation_exception_handler(request, exc)

        assert any("Validation error" in record.message for record in caplog.records)


class TestGenericExceptionHandler:
    """Tests for generic_exception_handler."""

    @pytest.mark.asyncio
    async def test_handle_unexpected_exception(self):
        """Test handling unexpected exceptions."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "req-unexpected"

        exc = ValueError("Unexpected error")

        response = await generic_exception_handler(request, exc)

        assert response.status_code == 500
        content = json.loads(response.body.decode())

        assert content["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected error occurred" in content["error"]["message"].lower()
        # Should not expose internal error details
        assert "ValueError" not in content["error"]["message"]

    @pytest.mark.asyncio
    async def test_generic_error_logging(self, caplog):
        """Test that generic errors are logged with traceback."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "req-trace"

        exc = RuntimeError("Test error")

        with caplog.at_level(logging.ERROR):
            await generic_exception_handler(request, exc)

        assert any("Unhandled exception" in record.message for record in caplog.records)


# ============================================================================
# Middleware Tests
# ============================================================================

class TestRequestIDMiddleware:
    """Tests for request_id_middleware."""

    @pytest.mark.asyncio
    async def test_adds_request_id(self):
        """Test that request ID is added to request state."""
        request = Mock(spec=Request)
        request.state = Mock()

        response = Mock()
        response.headers = {}

        async def call_next(req):
            # Verify request ID was set on state
            assert hasattr(req.state, "request_id")
            assert isinstance(req.state.request_id, str)
            return response

        result = await request_id_middleware(request, call_next)

        # Verify request ID in response headers
        assert "X-Request-ID" in result.headers
        assert result.headers["X-Request-ID"] == request.state.request_id

    @pytest.mark.asyncio
    async def test_request_id_is_uuid(self):
        """Test that request ID is a valid UUID."""
        import uuid

        request = Mock(spec=Request)
        request.state = Mock()

        response = Mock()
        response.headers = {}

        async def call_next(req):
            # Try to parse as UUID
            uuid.UUID(req.state.request_id)
            return response

        await request_id_middleware(request, call_next)


class TestErrorLoggingMiddleware:
    """Tests for error_logging_middleware."""

    @pytest.mark.asyncio
    async def test_logs_successful_request(self, caplog):
        """Test logging of successful requests."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/health"
        request.query_params = {}
        request.state.request_id = "req-123"

        response = Mock()
        response.status_code = 200

        async def call_next(req):
            return response

        with caplog.at_level(logging.INFO):
            await error_logging_middleware(request, call_next)

        # Check that request start and completion were logged
        messages = [record.message for record in caplog.records]
        assert any("Request started" in msg for msg in messages)
        assert any("Request completed" in msg for msg in messages)
        assert any("200" in msg for msg in messages)

    @pytest.mark.asyncio
    async def test_logs_failed_request(self, caplog):
        """Test logging of failed requests."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/query"
        request.query_params = {}
        request.state.request_id = "req-fail"

        async def call_next(req):
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                await error_logging_middleware(request, call_next)

        # Check that failure was logged
        assert any("Request failed" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_measures_request_duration(self, caplog):
        """Test that request duration is measured."""
        import asyncio

        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        request.query_params = {}
        request.state.request_id = "req-duration"

        response = Mock()
        response.status_code = 200

        async def call_next(req):
            await asyncio.sleep(0.01)  # 10ms delay
            return response

        with caplog.at_level(logging.INFO):
            await error_logging_middleware(request, call_next)

        # Check that duration was logged
        assert any("duration_ms" in str(record.__dict__) for record in caplog.records)


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestConfigureLogging:
    """Tests for configure_logging helper."""

    def test_configure_text_format(self):
        """Test configuring logging with text format."""
        configure_logging(level="DEBUG", format="text")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0

    def test_configure_json_format(self):
        """Test configuring logging with JSON format."""
        configure_logging(level="INFO", format="json")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_with_file(self, tmp_path):
        """Test configuring logging with file output."""
        log_file = tmp_path / "test.log"

        configure_logging(level="WARNING", format="text", log_file=str(log_file))

        root_logger = logging.getLogger()
        # Should have console + file handlers
        assert len(root_logger.handlers) >= 2

        # Test that logging works
        logger = logging.getLogger(__name__)
        logger.warning("Test message")

        assert log_file.exists()


# ============================================================================
# Integration Tests
# ============================================================================

class TestErrorHandlingIntegration:
    """Integration tests for complete error handling flow."""

    @pytest.mark.asyncio
    async def test_complete_error_flow(self):
        """Test complete error handling flow from exception to response."""
        # Setup request with request_id middleware
        request = Mock(spec=Request)
        request.url.path = "/api/query"
        request.state = Mock()

        # Add request ID
        response_mock = Mock()
        response_mock.headers = {}

        async def call_next_id(req):
            return response_mock

        await request_id_middleware(request, call_next_id)

        # Now handle an exception
        exc = APEValidationError(
            message="Query too short",
            details={"min_length": 10}
        )

        error_response = await ape_exception_handler(request, exc)

        # Verify complete response structure
        content = json.loads(error_response.body.decode())
        assert "error" in content
        assert content["error"]["code"] == "VALIDATION_ERROR"
        assert content["error"]["status"] == 422
        assert content["error"]["request_id"] == request.state.request_id
        assert content["error"]["path"] == "/api/query"
        assert "timestamp" in content["error"]

    @pytest.mark.asyncio
    async def test_middleware_chain(self):
        """Test that middlewares work together correctly."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"
        request.query_params = {}
        request.state = Mock()

        final_response = Mock()
        final_response.status_code = 200
        final_response.headers = {}

        async def endpoint(req):
            # Verify request ID was set by earlier middleware
            assert hasattr(req.state, "request_id")
            return final_response

        # Chain: request_id → error_logging → endpoint
        async def with_logging(req):
            return await error_logging_middleware(req, endpoint)

        result = await request_id_middleware(request, with_logging)

        # Verify request ID in response
        assert "X-Request-ID" in result.headers
