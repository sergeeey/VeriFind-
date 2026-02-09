"""
FastAPI REST API for APE 2026
Week 12 - Refactored: God Object → Clean Architecture

Endpoints:
- Health: /health, /ready, /live
- Analysis: /api/analyze, /api/query, /api/debate
- Data: /api/facts, /api/episodes, /api/status
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from .middleware import add_security_headers, add_disclaimer_to_json_responses
from .routes import health_router, analysis_router, data_router, predictions_router
from fastapi.exceptions import RequestValidationError
from .exceptions import APEException, ValidationError as APEValidationError

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

# Middleware (order matters!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
app.middleware("http")(request_id_middleware)
app.middleware("http")(error_logging_middleware)
app.middleware("http")(prometheus_middleware)
app.middleware("http")(add_security_headers)
app.middleware("http")(add_disclaimer_to_json_responses)

# Include routers
app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(data_router)
app.include_router(predictions_router)
