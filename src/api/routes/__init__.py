"""API Routes for APE 2026.

Week 12: Refactored from God Object main.py
Week 9 Day 3: Added Prediction Dashboard routes
"""

from .health import router as health_router
from .analysis import router as analysis_router
from .data import router as data_router
from .predictions import router as predictions_router

__all__ = ["health_router", "analysis_router", "data_router", "predictions_router"]
