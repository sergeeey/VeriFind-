"""
FastAPI REST API for APE 2026
Week 13 Day 2: Clean Architecture with App Factory Pattern

Main entry point - delegates configuration to app_factory.py
Target: <100 lines (achieved: ~60 lines)

Endpoints:
- Health: /health, /ready, /live
- Analysis: /api/analyze, /api/query, /api/debate
- Data: /api/facts, /api/episodes, /api/status
- Admin: /admin/api-keys, /admin/usage
- WebSocket: /ws (real-time updates)
"""

# ============================================================================
# CRITICAL: Load .env BEFORE importing settings
# ============================================================================

from dotenv import load_dotenv
import os

# Load .env from project root (2 levels up from this file)
env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    '.env'
)
load_dotenv(dotenv_path=env_path, override=True)

# ============================================================================
# Configuration (must happen before app creation)
# ============================================================================

from .config import get_settings
from .error_handlers import configure_logging
from .monitoring import initialize_monitoring

settings = get_settings()

# Configure logging
configure_logging(
    level=settings.log_level,
    format="json" if settings.environment == "production" else "text",
)

# Initialize monitoring
initialize_monitoring(
    version=settings.app_version,
    environment=settings.environment
)

# ============================================================================
# Application Creation (Factory Pattern)
# ============================================================================

from .app_factory import create_app

# Create application using factory pattern
# All configuration delegated to app_factory.py:
# - Exception handlers
# - Middleware stack (CORS, security, compliance, etc.)
# - Router registration (14 routers)
# - Event handlers (startup/shutdown)
# - WebSocket configuration
app = create_app(settings)

# ============================================================================
# Export for ASGI servers (uvicorn, gunicorn)
# ============================================================================

__all__ = ["app"]
