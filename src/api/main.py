"""
FastAPI REST API for APE 2026
Week 12 - Refactored: God Object → Clean Architecture

Endpoints:
- Health: /health, /ready, /live
- Analysis: /api/analyze, /api/query, /api/debate
- Data: /api/facts, /api/episodes, /api/status
"""

# CRITICAL: Load .env file BEFORE importing settings
from dotenv import load_dotenv
import os

# Load .env from project root (2 levels up from this file)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path, override=True)

from fastapi import FastAPI
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4

from .config import get_settings
from .error_handlers import (
    ape_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    request_id_middleware,
    error_logging_middleware,
    configure_logging,
)
from .monitoring import prometheus_middleware, initialize_monitoring
from .middleware import add_security_headers, add_disclaimer_to_json_responses, add_rate_limit_headers
from .middleware.compliance import ComplianceMiddleware
from .routes import (
    health_router,
    analysis_router,
    data_router,
    predictions_router,
    audit_router,
    history_router,
    portfolio_router,
    alerts_router,
    sensitivity_router,
    educational_router,
    sec_router,
    sentiment_router,
    report_router,
)
from .routes.admin_api_keys import router as admin_api_keys_router
from .routes.admin_usage import router as admin_usage_router
from fastapi.exceptions import RequestValidationError
from .exceptions import APEException, ValidationError as APEValidationError
from ..predictions.scheduler import prediction_scheduler
from ..alerts.scheduler import price_alert_scheduler
from .websocket import websocket_handler

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

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Exception handlers
app.add_exception_handler(APEException, ape_exception_handler)
app.add_exception_handler(APEValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CRITICAL: Middleware order matters!
# 1. CORS first (must process OPTIONS requests)
# 2. Security headers early
# 3. Cache (can skip other middleware on HIT)
# 4. Request tracking (profiling, request_id)
# 5. Processing (rate limit, logging)
# 6. Disclaimer LAST (modifies response)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Security headers (early)
app.middleware("http")(add_security_headers)
app.middleware("http")(add_rate_limit_headers)

# Usage tracking (logs requests for billing, enforces quota)
from .usage.middleware import log_request_middleware, enforce_quota_middleware
app.middleware("http")(enforce_quota_middleware)  # FIRST: Check quota before processing
app.middleware("http")(log_request_middleware)    # THEN: Log the request

# DISABLED: Route-level caching is faster and more reliable
# Middleware caching causes issues with response body iteration
# See: src/api/routes/analysis.py for route-level cache implementation
# if settings.cache_enabled:
#     from .middleware.cache import ResponseCacheMiddleware
#     app.add_middleware(
#         ResponseCacheMiddleware,
#         redis_url=settings.redis_url
#     )

# Profiling (tracks timing)
if settings.profiling_enabled:
    from .middleware.profiling import ProfilingMiddleware
    app.add_middleware(
        ProfilingMiddleware,
        slow_threshold=settings.profiling_slow_threshold
    )

# Request tracking
app.middleware("http")(request_id_middleware)
app.middleware("http")(prometheus_middleware)

# Logging (after processing)
app.middleware("http")(error_logging_middleware)

# Compliance middleware (audit logging for financial analysis)
app.add_middleware(ComplianceMiddleware)

# Disclaimer LAST (modifies JSON response)
app.middleware("http")(add_disclaimer_to_json_responses)

# Include routers
app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(data_router)
app.include_router(predictions_router)
app.include_router(audit_router)
app.include_router(history_router)
app.include_router(portfolio_router)
app.include_router(alerts_router)
app.include_router(sensitivity_router)
app.include_router(educational_router)
app.include_router(sec_router)
app.include_router(sentiment_router)
app.include_router(report_router)

# Admin routers (Week 12 - B2B API)
app.include_router(admin_api_keys_router)
app.include_router(admin_usage_router)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time query status updates."""
    connection_id = str(uuid4())
    await websocket_handler(websocket, connection_id)


@app.on_event("startup")
async def start_prediction_scheduler():
    """Start daily prediction evaluation scheduler."""
    prediction_scheduler.start(db_url=settings.timescaledb_url)
    price_alert_scheduler.start(db_url=settings.timescaledb_url)


@app.on_event("shutdown")
async def stop_prediction_scheduler():
    """Stop scheduler on app shutdown."""
    prediction_scheduler.stop()
    price_alert_scheduler.stop()
