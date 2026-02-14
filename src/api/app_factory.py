"""
Application Factory for APE 2026 FastAPI App

Week 13 Day 2: Extracted from main.py for Clean Architecture
Factory pattern enables:
- Testable app creation with different settings
- Multiple app instances (prod/test/dev)
- Clean dependency injection
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .config import APISettings, get_settings
from .error_handlers import (
    ape_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    request_id_middleware,
    error_logging_middleware,
)
from .monitoring import prometheus_middleware
from .middleware import (
    add_security_headers,
    add_disclaimer_to_json_responses,
    add_rate_limit_headers,
)
from .middleware.compliance import ComplianceMiddleware
from .exceptions import APEException, ValidationError as APEValidationError


def configure_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers for the application."""
    app.add_exception_handler(APEException, ape_exception_handler)
    app.add_exception_handler(APEValidationError, validation_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


def configure_middleware(app: FastAPI, settings: APISettings) -> None:
    """
    Configure middleware stack in correct order.

    CRITICAL: Middleware order matters!
    1. CORS first (must process OPTIONS requests)
    2. Security headers early
    3. Usage tracking (quota enforcement + logging)
    4. Profiling (if enabled)
    5. Request tracking (request_id, prometheus)
    6. Error logging
    7. Compliance (audit trail)
    8. Disclaimer LAST (modifies response)
    """
    # 1. CORS first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # 2. Security headers
    app.middleware("http")(add_security_headers)
    app.middleware("http")(add_rate_limit_headers)

    # 3. Usage tracking (quota + logging)
    from .usage.middleware import log_request_middleware, enforce_quota_middleware
    app.middleware("http")(enforce_quota_middleware)  # Check quota first
    app.middleware("http")(log_request_middleware)    # Then log

    # 4. Profiling (optional)
    if settings.profiling_enabled:
        from .middleware.profiling import ProfilingMiddleware
        app.add_middleware(
            ProfilingMiddleware,
            slow_threshold=settings.profiling_slow_threshold
        )

    # 5. Request tracking
    app.middleware("http")(request_id_middleware)
    app.middleware("http")(prometheus_middleware)

    # 6. Error logging
    app.middleware("http")(error_logging_middleware)

    # 7. Compliance (audit trail)
    app.add_middleware(ComplianceMiddleware)

    # 8. Disclaimer LAST (modifies JSON response)
    app.middleware("http")(add_disclaimer_to_json_responses)


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
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

    # Core routers
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


def configure_events(app: FastAPI, settings: APISettings) -> None:
    """Configure startup and shutdown events."""
    from ..predictions.scheduler import prediction_scheduler
    from ..alerts.scheduler import price_alert_scheduler

    @app.on_event("startup")
    async def startup():
        """Start schedulers on app startup."""
        prediction_scheduler.start(db_url=settings.timescaledb_url)
        price_alert_scheduler.start(db_url=settings.timescaledb_url)

    @app.on_event("shutdown")
    async def shutdown():
        """Stop schedulers on app shutdown."""
        prediction_scheduler.stop()
        price_alert_scheduler.stop()


def configure_websocket(app: FastAPI) -> None:
    """Configure WebSocket endpoints."""
    from fastapi import WebSocket
    from uuid import uuid4
    from .websocket import websocket_handler

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time query status updates."""
        connection_id = str(uuid4())
        await websocket_handler(websocket, connection_id)


def create_app(settings: APISettings = None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        settings: Application settings (defaults to get_settings())

    Returns:
        Configured FastAPI app instance

    Factory pattern benefits:
    - Testable: can pass mock settings
    - Flexible: multiple app instances
    - Clean: clear dependency injection
    """
    if settings is None:
        settings = get_settings()

    # Create app
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Configure components
    configure_exception_handlers(app)
    configure_middleware(app, settings)
    register_routers(app)
    configure_events(app, settings)
    configure_websocket(app)

    return app
