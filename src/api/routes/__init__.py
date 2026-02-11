"""API Routes for APE 2026.

Week 12: Refactored from God Object main.py
Week 9 Day 3: Added Prediction Dashboard routes
"""

from .health import router as health_router
from .analysis import router as analysis_router
from .data import router as data_router
from .predictions import router as predictions_router
from .audit import router as audit_router
from .history import router as history_router
from .portfolio import router as portfolio_router
from .alerts import router as alerts_router
from .sensitivity import router as sensitivity_router
from .educational import router as educational_router
from .sec import router as sec_router
from .sentiment import router as sentiment_router
from .report import router as report_router

__all__ = [
    "health_router",
    "analysis_router",
    "data_router",
    "predictions_router",
    "audit_router",
    "history_router",
    "portfolio_router",
    "alerts_router",
    "sensitivity_router",
    "educational_router",
    "sec_router",
    "sentiment_router",
    "report_router",
]
