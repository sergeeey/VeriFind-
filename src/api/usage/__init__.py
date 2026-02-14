"""
Usage Tracking Module.

Week 12 Day 2-3: Request logging, cost tracking, billing.

Note: SQLAlchemy 2.0.27 incompatible with Python 3.13.5
Usage tracking disabled in Python 3.13+ environments (beta workaround)
"""

import sys

# Graceful degradation for Python 3.13+ (SQLAlchemy incompatibility)
if sys.version_info >= (3, 13):
    # Stub implementations for beta
    class UsageLogger:
        pass

    def get_usage_logger():
        return None

    class CostCalculator:
        pass

    api_usage_logs = []

    async def log_request_middleware(request, call_next):
        return await call_next(request)

    async def enforce_quota_middleware(request, call_next):
        return await call_next(request)

    def set_request_cost(cost):
        pass
else:
    from .usage_logger import (
        UsageLogger,
        get_usage_logger,
        CostCalculator,
        api_usage_logs
    )
    from .middleware import (
        log_request_middleware,
        enforce_quota_middleware,
        set_request_cost
    )

__all__ = [
    "UsageLogger",
    "get_usage_logger",
    "CostCalculator",
    "api_usage_logs",
    "log_request_middleware",
    "enforce_quota_middleware",
    "set_request_cost"
]
