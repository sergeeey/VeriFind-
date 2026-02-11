"""
Usage Tracking Middleware for FastAPI.

Week 12 Day 2: Automatic request logging and quota enforcement.

Usage:
    from src.api.usage.middleware import log_request_middleware

    app.middleware("http")(log_request_middleware)
"""

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import time
import logging
import json

from .usage_logger import get_usage_logger
from src.api.auth.api_key_manager import get_api_key_manager


logger = logging.getLogger(__name__)


def set_request_cost(request: Request, cost_usd: float, tokens_used: Optional[int] = None, llm_provider: Optional[str] = None):
    """
    Set cost information on request state for middleware to log.

    Endpoints should call this function to report LLM costs:

    Example:
        from src.api.usage.middleware import set_request_cost

        @app.post("/api/analyze-debate")
        async def analyze_debate(request: Request):
            result = await run_debate(...)
            set_request_cost(request, cost_usd=0.0025, tokens_used=1500, llm_provider="multi-llm")
            return result

    Args:
        request: FastAPI request object
        cost_usd: Cost in USD
        tokens_used: Number of tokens used (optional)
        llm_provider: LLM provider name (optional)
    """
    request.state.cost_usd = cost_usd
    if tokens_used is not None:
        request.state.tokens_used = tokens_used
    if llm_provider is not None:
        request.state.llm_provider = llm_provider


async def log_request_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware: Log all API requests for usage tracking.

    Automatically logs:
    - Endpoint, method, status code
    - Response time
    - API key (if present)
    - Cost (if available in response)

    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint

    Returns:
        Response
    """
    start_time = time.time()

    # Extract API key from header
    api_key = request.headers.get("X-API-Key")

    # Process request
    response = await call_next(request)

    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)

    # Log request (only if API key present)
    if api_key:
        try:
            # Get API key info
            key_manager = await get_api_key_manager()
            key_info = await key_manager.get_key_info(api_key)

            if key_info:
                # Extract cost from request.state (set by endpoint using set_request_cost())
                cost_usd = getattr(request.state, "cost_usd", 0.0)
                tokens_used = getattr(request.state, "tokens_used", None)
                llm_provider = getattr(request.state, "llm_provider", None)

                # Log to usage tracker
                usage_logger = await get_usage_logger()
                await usage_logger.log_request(
                    api_key_id=key_info['id'],
                    customer_name=key_info['customer_name'],
                    tier=key_info['tier'],
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    cost_usd=cost_usd,
                    tokens_used=tokens_used,
                    llm_provider=llm_provider,
                    user_agent=request.headers.get("User-Agent"),
                    ip_address=request.client.host if request.client else None
                )

        except Exception as e:
            logger.error(f"Failed to log request: {e}")
            # Don't fail the request if logging fails

    return response


async def enforce_quota_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware: Enforce monthly quota limits.

    Returns 429 Too Many Requests if quota exceeded.

    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint

    Returns:
        Response

    Raises:
        HTTPException: 429 if quota exceeded
    """
    # Extract API key from header
    api_key = request.headers.get("X-API-Key")

    if api_key:
        try:
            # Get API key info
            key_manager = await get_api_key_manager()
            key_info = await key_manager.get_key_info(api_key)

            if key_info and key_info['monthly_quota'] is not None:
                # Check quota
                usage_logger = await get_usage_logger()
                within_quota, used, remaining = await usage_logger.check_quota(
                    api_key_id=key_info['id'],
                    monthly_quota=key_info['monthly_quota']
                )

                if not within_quota:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Monthly quota exceeded ({used}/{key_info['monthly_quota']} requests used)",
                        headers={
                            "X-RateLimit-Limit": str(key_info['monthly_quota']),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": "1st of next month"
                        }
                    )

                # Add rate limit headers to response
                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(key_info['monthly_quota'])
                response.headers["X-RateLimit-Remaining"] = str(remaining)

                return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to check quota: {e}")
            # Don't fail the request if quota check fails

    # No API key or unlimited quota - proceed normally
    return await call_next(request)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Combined usage tracking and quota enforcement middleware.

    Usage:
        app.add_middleware(UsageTrackingMiddleware)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with usage tracking and quota enforcement.

        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint

        Returns:
            Response
        """
        # First check quota
        await enforce_quota_middleware(request, lambda r: r)

        # Then log request
        return await log_request_middleware(request, call_next)
