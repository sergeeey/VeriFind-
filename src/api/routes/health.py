"""Health and monitoring routes.

Week 12: Extracted from main.py God Object
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
from pathlib import Path
import logging

from ..monitoring import get_health_metrics
from ..config import get_settings
from ...predictions.scheduler import prediction_scheduler
from ...alerts.scheduler import price_alert_scheduler
from ..middleware.rate_limit import get_usage_summary_snapshot
from .analysis import get_orchestrator_instance

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Legal Disclaimer Constants
LEGAL_DISCLAIMER = {
    "text": (
        "This analysis is for informational purposes only and should not be considered "
        "financial advice. Past performance does not guarantee future results. "
        "Always consult a qualified financial advisor before making investment decisions."
    ),
    "version": "1.0",
    "effective_date": "2026-02-08",
}


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    metrics = get_health_metrics()
    return {
        "status": "healthy" if all(v == "up" for v in metrics.values()) else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "components": metrics,
        "disclaimer": LEGAL_DISCLAIMER["text"]
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Kubernetes readiness probe."""
    metrics = get_health_metrics()
    is_ready = all(v == "up" for v in metrics.values())
    return {
        "status": "ready" if is_ready else "not_ready",
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive", "alive": True}


@router.get("/disclaimer", status_code=status.HTTP_200_OK)
async def get_disclaimer():
    """Get full legal disclaimer."""
    disclaimer_path = Path(__file__).parent.parent.parent.parent / "DISCLAIMER.md"
    
    full_text = LEGAL_DISCLAIMER["text"]
    if disclaimer_path.exists():
        try:
            full_text = disclaimer_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read DISCLAIMER.md: {e}")
    
    return {
        "disclaimer": LEGAL_DISCLAIMER,
        "full_text": full_text,
        "notice": (
            "By using this API, you acknowledge that you have read, understood, "
            "and agree to be bound by this disclaimer."
        ),
        "summary": "Not financial advice - consult a qualified advisor"
    }


@router.get("/metrics/performance", status_code=status.HTTP_200_OK)
async def performance_metrics():
    """Get API performance metrics."""
    from ..middleware.profiling import ProfilingMiddleware
    from ..middleware.cache import CacheStats
    import redis.asyncio as redis
    
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "cache": {},
        "profiling": {},
        "settings": {
            "cache_enabled": settings.cache_enabled,
            "profiling_enabled": settings.profiling_enabled,
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "profiling_slow_threshold": settings.profiling_slow_threshold
        }
    }
    
    # Get cache stats
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        cache_stats = CacheStats(redis_client)
        metrics["cache"] = await cache_stats.get_stats()
        await redis_client.close()
    except Exception as e:
        metrics["cache"] = {"error": str(e)}
    
    # Note: Profiling stats would need to be accessed from the middleware instance
    # This is a simplified version
    
    return metrics


@router.get("/api/health/scheduler", status_code=status.HTTP_200_OK)
async def scheduler_health():
    """Prediction scheduler health endpoint."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler": prediction_scheduler.health(),
    }


@router.get("/api/health/alerts-scheduler", status_code=status.HTTP_200_OK)
async def alerts_scheduler_health():
    """Price alerts scheduler health endpoint."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler": price_alert_scheduler.health(),
    }


@router.get("/api/usage/summary", status_code=status.HTTP_200_OK)
async def usage_summary():
    """API usage snapshot for rate limiting and key consumption trends."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "usage": get_usage_summary_snapshot(),
    }


@router.get("/api/health/circuit-breakers", status_code=status.HTTP_200_OK)
async def circuit_breakers_health():
    """Expose circuit breaker states for operational diagnostics."""
    instance = get_orchestrator_instance()
    orchestrator = instance.get("orchestrator")
    provider = instance.get("provider")

    if orchestrator is None:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": None,
            "initialized": False,
            "message": "Orchestrator not initialized yet. Run /api/analyze or /api/debate first.",
            "breakers": {},
        }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "provider": provider,
        "initialized": True,
        "breakers": {
            "market_data_fetch": orchestrator.market_data_breaker.get_stats(),
            "llm_debate": orchestrator.llm_debate_breaker.get_stats(),
        },
    }
