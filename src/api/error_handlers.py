"""
Centralized error handlers for APE API.

Week 9 Day 2: Exception handling and error responses.
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError

from .exceptions import (
    APEException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    get_error_severity
)

logger = logging.getLogger(__name__)


# ============================================================================
# Error Response Models
# ============================================================================

class ErrorResponse:
    """
    Standardized error response format.

    Format follows RFC 7807 (Problem Details for HTTP APIs).
    """

    @staticmethod
    def create(
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized error response.

        Args:
            status_code: HTTP status code
            error_code: Machine-readable error code
            message: Human-readable error message
            details: Additional error details
            request_id: Request ID for tracking
            path: Request path

        Returns:
            Error response dictionary
        """
        response = {
            "error": {
                "code": error_code,
                "message": message,
                "status": status_code,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

        if details:
            response["error"]["details"] = details

        if request_id:
            response["error"]["request_id"] = request_id

        if path:
            response["error"]["path"] = path

        return response


# ============================================================================
# Exception Handlers
# ============================================================================

async def ape_exception_handler(request: Request, exc: APEException) -> JSONResponse:
    """
    Handle APE custom exceptions.

    Args:
        request: FastAPI request
        exc: APE exception

    Returns:
        JSON error response
    """
    # Get request ID if available
    request_id = getattr(request.state, "request_id", None)

    # Log error with severity
    severity = get_error_severity(exc)
    log_level = getattr(logging, severity.upper(), logging.ERROR)

    logger.log(
        log_level,
        f"APE Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "request_id": request_id,
            "path": request.url.path
        }
    )

    # Create error response
    error_response = ErrorResponse.create(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
        path=request.url.path
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic/FastAPI validation errors.

    Args:
        request: FastAPI request
        exc: Validation error

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)

    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation error: {len(errors)} field(s) failed validation",
        extra={
            "validation_errors": errors,
            "request_id": request_id,
            "path": request.url.path
        }
    )

    error_response = ErrorResponse.create(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"validation_errors": errors},
        request_id=request_id,
        path=request.url.path
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected/unhandled exceptions.

    Args:
        request: FastAPI request
        exc: Any exception

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)

    # Log full traceback for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_id": request_id,
            "path": request.url.path,
            "traceback": traceback.format_exc()
        }
    )

    # Don't expose internal error details in production
    error_response = ErrorResponse.create(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        details={"request_id": request_id} if request_id else None,
        request_id=request_id,
        path=request.url.path
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


# ============================================================================
# Middleware
# ============================================================================

async def request_id_middleware(request: Request, call_next):
    """
    Add unique request ID to each request.

    Useful for tracking errors across logs.
    """
    import uuid

    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Add to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


async def error_logging_middleware(request: Request, call_next):
    """
    Log all requests and errors.

    Captures:
    - Request method, path, query params
    - Response status code
    - Execution time
    - Errors
    """
    import time

    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")

    # Log request
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "request_id": request_id
        }
    )

    try:
        response = await call_next(request)

        # Log response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id
            }
        )

        return response

    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000

        logger.error(
            f"Request failed: {request.method} {request.url.path} - {type(exc).__name__}",
            exc_info=True,
            extra={
                "method": request.method,
                "path": request.url.path,
                "exception": type(exc).__name__,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id
            }
        )

        raise


# ============================================================================
# Helper Functions
# ============================================================================

def configure_logging(
    level: str = "INFO",
    format: str = "json",
    log_file: Optional[str] = None
):
    """
    Configure structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log format ("json" or "text")
        log_file: Optional log file path
    """
    import sys
    from logging.handlers import RotatingFileHandler

    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Create formatter
    if format == "json":
        try:
            import json_log_formatter

            formatter = json_log_formatter.JSONFormatter()
        except ImportError:
            # Fallback to standard formatter
            formatter = logging.Formatter(
                '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
            )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logger.info(f"Logging configured: level={level}, format={format}")
