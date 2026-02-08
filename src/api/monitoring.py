"""
Monitoring middleware and utilities for APE API.

Week 9 Day 2: Prometheus integration and metrics collection.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_response_size_bytes,
    http_requests_in_progress,
    set_app_info
)

logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus Metrics Middleware
# ============================================================================

async def prometheus_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to collect Prometheus metrics for all HTTP requests.

    Collects:
    - Request count by method, endpoint, status
    - Request duration
    - Request/response sizes
    - Requests in progress
    """
    # Extract endpoint and method
    method = request.method
    endpoint = request.url.path

    # Skip metrics endpoint itself to avoid recursion
    if endpoint == "/metrics":
        return await call_next(request)

    # Track request size
    request_size = int(request.headers.get("content-length", 0))
    http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(request_size)

    # Increment in-progress counter
    http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

    # Start timer
    start_time = time.time()

    try:
        # Process request
        response = await call_next(request)

        # Record metrics
        status = response.status_code
        duration = time.time() - start_time

        # Increment request counter
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        # Record duration
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        # Track response size
        response_size = int(response.headers.get("content-length", 0))
        http_response_size_bytes.labels(
            method=method,
            endpoint=endpoint
        ).observe(response_size)

        # Log slow requests (> 1 second)
        if duration > 1.0:
            logger.warning(
                f"Slow request: {method} {endpoint} - {duration:.2f}s",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "duration_seconds": duration,
                    "status": status
                }
            )

        return response

    except Exception as e:
        # Record exception
        duration = time.time() - start_time

        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=500
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        logger.error(
            f"Request failed: {method} {endpoint} - {type(e).__name__}",
            exc_info=True,
            extra={
                "method": method,
                "endpoint": endpoint,
                "duration_seconds": duration,
                "exception": type(e).__name__
            }
        )

        raise

    finally:
        # Decrement in-progress counter
        http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


# ============================================================================
# Metrics Endpoint
# ============================================================================

def metrics_endpoint() -> Response:
    """
    Expose Prometheus metrics endpoint.

    Returns:
        Response with Prometheus-formatted metrics
    """
    metrics = generate_latest()
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)


# ============================================================================
# Application Startup
# ============================================================================

def initialize_monitoring(version: str, environment: str):
    """
    Initialize monitoring system.

    Args:
        version: Application version
        environment: Environment (development, staging, production)
    """
    # Set application info
    set_app_info(version=version, environment=environment)

    logger.info(
        f"Monitoring initialized: version={version}, environment={environment}"
    )


# ============================================================================
# Health Check with Metrics
# ============================================================================

def get_health_metrics() -> dict:
    """
    Get health metrics for monitoring.

    Returns:
        Dictionary with health metrics
    """
    from prometheus_client import REGISTRY

    # Collect all metrics
    metrics = {}

    for metric in REGISTRY.collect():
        for sample in metric.samples:
            metrics[sample.name] = sample.value

    return {
        "total_requests": metrics.get("http_requests_total", 0),
        "requests_in_progress": metrics.get("http_requests_in_progress", 0),
        "total_queries": metrics.get("queries_submitted_total", 0),
        "total_facts": metrics.get("verified_facts_generated_total", 0),
        "websocket_connections": metrics.get("websocket_connections_total", 0),
        "cache_hit_ratio": metrics.get("cache_hit_ratio", 0.0)
    }
