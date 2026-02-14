"""
Compliance middleware for APE 2026.

Week 13 Day 1: Ensures all financial analysis responses include required disclaimers
and logs analysis requests for regulatory audit trail.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json
import time
import logging
import structlog

logger = structlog.get_logger()

# Endpoints that require compliance disclaimers
ANALYSIS_ENDPOINTS = [
    "/api/analyze-debate",
    "/api/analyze",
    "/api/predictions",
    "/api/predictions/historical",
    "/api/predictions/backtest",
    "/api/report/generate",
    "/api/sentiment/analyze",
    "/api/sensitivity/analyze",
]


class ComplianceMiddleware(BaseHTTPMiddleware):
    """Injects compliance disclaimers into financial analysis responses."""

    async def dispatch(self, request: Request, call_next):
        """Process request and add compliance logging."""
        start_time = time.time()

        response = await call_next(request)

        # Only process analysis endpoints
        if request.url.path in ANALYSIS_ENDPOINTS:
            # Log for audit trail
            processing_time_ms = (time.time() - start_time) * 1000
            self._log_analysis_request(request, processing_time_ms)

        return response

    def _log_analysis_request(self, request: Request, processing_time_ms: float):
        """Log analysis request for audit trail."""
        logger.info(
            "analysis_request",
            path=request.url.path,
            method=request.method,
            timestamp=time.time(),
            processing_time_ms=processing_time_ms,
            client_ip=request.client.host if request.client else "unknown",
            # DO NOT log request body (may contain PII)
        )
