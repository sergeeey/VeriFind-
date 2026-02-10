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
