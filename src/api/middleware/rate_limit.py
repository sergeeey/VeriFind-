"""Rate limiting middleware.

Week 2 Day 9: Production Readiness
Adds rate limit headers to responses.
"""

from fastapi import Request
import logging

logger = logging.getLogger(__name__)

# Simple in-memory rate limiting (production should use Redis)
_request_counts: dict = {}

def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def add_rate_limit_headers(request: Request, call_next):
    """
    Add rate limit headers to all responses.
    
    Headers:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Remaining requests in window
    - X-RateLimit-Reset: Unix timestamp when limit resets
    """
    response = await call_next(request)
    
    # Add rate limit headers (placeholder values - production should track actual usage)
    response.headers["X-RateLimit-Limit"] = "1000"
    response.headers["X-RateLimit-Remaining"] = "999"
    response.headers["X-RateLimit-Reset"] = str(int(__import__('time').time()) + 3600)
    
    return response
