"""Rate limiting middleware with usage accounting and dashboard helpers."""

from datetime import datetime, timedelta
import os
import time
import logging
from typing import Dict, List

from fastapi import Request
from fastapi.responses import JSONResponse

from ..config import get_settings, load_production_api_keys
from ..metrics import record_rate_limit_violation

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory stores (Redis-backed limiter is recommended for multi-instance production)
_request_timestamps: Dict[str, List[datetime]] = {}
_usage_totals: Dict[str, int] = {}
_last_seen: Dict[str, datetime] = {}


def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforcement_enabled() -> bool:
    """Feature flag for hard enforcement in middleware path."""
    raw = os.getenv("RATE_LIMIT_ENFORCEMENT", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _resolve_limit(api_key: str | None) -> int:
    """Resolve per-key limit or fallback to default limit."""
    all_keys = {**settings.api_keys, **load_production_api_keys()}
    if api_key and api_key in all_keys:
        return int(all_keys[api_key].get("rate_limit", settings.default_rate_limit))
    return int(settings.default_rate_limit)


def _identity_for_request(request: Request) -> str:
    """Stable identity for accounting (api key preferred, fallback to IP)."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    return f"ip:{get_client_ip(request)}"


def _compact_window(identity: str, now: datetime, window: timedelta):
    """Drop timestamps outside current rate-limit window."""
    if identity not in _request_timestamps:
        _request_timestamps[identity] = []
        return
    _request_timestamps[identity] = [
        ts for ts in _request_timestamps[identity]
        if now - ts < window
    ]


def _mask_identity(identity: str) -> str:
    """Mask key identities for safe dashboard output."""
    if identity.startswith("key:"):
        raw_key = identity[4:]
        if len(raw_key) <= 8:
            return "key:****"
        return f"key:{raw_key[:4]}...{raw_key[-4:]}"
    if identity.startswith("ip:"):
        ip = identity[3:]
        return f"ip:{ip}"
    return "unknown"


def get_usage_summary_snapshot() -> Dict[str, object]:
    """Return current usage snapshot for dashboard endpoint."""
    window = timedelta(hours=settings.rate_limit_window_hours)
    now = datetime.utcnow()

    consumers = []
    for identity in list(_request_timestamps.keys()):
        _compact_window(identity, now, window)
        current_window_count = len(_request_timestamps.get(identity, []))
        consumers.append({
            "consumer": _mask_identity(identity),
            "requests_current_window": current_window_count,
            "requests_total": int(_usage_totals.get(identity, 0)),
            "last_seen": (
                _last_seen.get(identity).isoformat()
                if _last_seen.get(identity) else None
            ),
        })

    consumers.sort(key=lambda item: item["requests_total"], reverse=True)

    return {
        "enforcement_enabled": _enforcement_enabled(),
        "window_hours": int(settings.rate_limit_window_hours),
        "default_limit": int(settings.default_rate_limit),
        "active_consumers": len(consumers),
        "consumers": consumers[:20],
    }


def _reset_rate_limit_state_for_tests():
    """Reset middleware state (for tests only)."""
    _request_timestamps.clear()
    _usage_totals.clear()
    _last_seen.clear()


async def add_rate_limit_headers(request: Request, call_next):
    """
    Apply per-consumer accounting and set standard rate-limit headers.

    Uses X-API-Key limits when available; otherwise falls back to default IP-based limits.
    """
    now = datetime.utcnow()
    window = timedelta(hours=settings.rate_limit_window_hours)
    reset_epoch = int((now + window).timestamp())
    api_key = request.headers.get("X-API-Key")
    identity = _identity_for_request(request)
    limit = _resolve_limit(api_key)

    _compact_window(identity, now, window)
    current_count = len(_request_timestamps.get(identity, []))

    if _enforcement_enabled() and current_count >= limit:
        record_rate_limit_violation(api_key or "anonymous")
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_epoch),
        }
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
            headers=headers,
        )

    # Account request before processing to keep remaining header consistent.
    _request_timestamps.setdefault(identity, []).append(now)
    _usage_totals[identity] = _usage_totals.get(identity, 0) + 1
    _last_seen[identity] = now

    response = await call_next(request)

    remaining = max(0, limit - len(_request_timestamps.get(identity, [])))
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_epoch)
    return response
