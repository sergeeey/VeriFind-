# main.py Refactoring Plan — Task 5

**Current State:** 182 lines
**Target:** <100 lines
**Strategy:** Extract app factory, middleware configuration, router registration

---

## Current Analysis

### What's Good ✅
- Routers already extracted (14 routers)
- Middleware already modularized
- Exception handlers centralized
- Clear separation of concerns

### What Can Improve 🔄
- **Lines 11-72:** Configuration and initialization (62 lines) → Extract to `create_app()` factory
- **Lines 74-142:** App creation and middleware setup (68 lines) → Extract to `configure_middleware()`
- **Lines 144-161:** Router registration (18 lines) → Extract to `register_routers()`
- **Lines 164-182:** Event handlers and WebSocket (19 lines) → Extract to `configure_events()`

---

## Refactoring Strategy

### Phase 1: Create App Factory Pattern
Extract to `src/api/app_factory.py`:

```python
def create_app(settings: Settings = None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Factory pattern allows:
    - Testing with different settings
    - Multiple app instances
    - Clean dependency injection
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(...)

    configure_exception_handlers(app)
    configure_middleware(app, settings)
    register_routers(app)
    configure_events(app, settings)

    return app
```

### Phase 2: Extract Middleware Configuration
Extract to `src/api/middleware_config.py`:

```python
def configure_middleware(app: FastAPI, settings: Settings) -> None:
    """Configure all middleware in correct order."""
    # CORS
    app.add_middleware(CORSMiddleware, ...)

    # Security
    app.middleware("http")(add_security_headers)
    app.middleware("http")(add_rate_limit_headers)

    # ... rest
```

### Phase 3: Extract Router Registration
Extract to `src/api/router_config.py`:

```python
def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    routers = [
        health_router,
        analysis_router,
        # ... all 14 routers
    ]

    for router in routers:
        app.include_router(router)
```

### Phase 4: Extract Event Configuration
Extract to `src/api/events_config.py`:

```python
def configure_events(app: FastAPI, settings: Settings) -> None:
    """Configure startup and shutdown events."""

    @app.on_event("startup")
    async def startup():
        prediction_scheduler.start(db_url=settings.timescaledb_url)
        price_alert_scheduler.start(db_url=settings.timescaledb_url)

    @app.on_event("shutdown")
    async def shutdown():
        prediction_scheduler.stop()
        price_alert_scheduler.stop()
```

### Phase 5: Final main.py (Target: <50 lines)

```python
"""
FastAPI REST API for APE 2026
Week 13 - Clean Architecture Pattern

Main entry point using app factory pattern.
Configuration extracted to separate modules for testability.
"""

# CRITICAL: Load .env file BEFORE importing settings
from dotenv import load_dotenv
import os

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path, override=True)

from .app_factory import create_app
from .config import get_settings

# Configure logging and monitoring (must happen before app creation)
from .error_handlers import configure_logging
from .monitoring import initialize_monitoring

settings = get_settings()

configure_logging(
    level=settings.log_level,
    format="json" if settings.environment == "production" else "text",
)

initialize_monitoring(
    version=settings.app_version,
    environment=settings.environment
)

# Create application using factory pattern
app = create_app(settings)
```

---

## Benefits

### Testability 🧪
- Can create test app with mock settings
- Easier to test middleware order
- Isolated component testing

### Maintainability 🔧
- Clear separation of concerns
- Each file has single responsibility
- Easy to find and modify configuration

### Scalability 📈
- New middleware → add to middleware_config.py
- New router → add to router_config.py
- No need to touch main.py

---

## File Structure (After Refactoring)

```
src/api/
├── main.py                    # 40-50 lines (entry point)
├── app_factory.py            # 60-80 lines (create_app)
├── middleware_config.py      # 80-100 lines (configure_middleware)
├── router_config.py          # 40-50 lines (register_routers)
├── events_config.py          # 30-40 lines (configure_events)
├── exception_config.py       # 30-40 lines (configure_exception_handlers)
├── config.py                 # existing
├── error_handlers.py         # existing
├── monitoring.py             # existing
└── routes/                   # existing
```

---

## Implementation Order

1. ✅ Create `exception_config.py` (extract exception handler registration)
2. ✅ Create `middleware_config.py` (extract middleware setup)
3. ✅ Create `router_config.py` (extract router registration)
4. ✅ Create `events_config.py` (extract event handlers)
5. ✅ Create `app_factory.py` (combine everything)
6. ✅ Update `main.py` (minimal entry point)
7. ✅ Run tests to verify nothing broke
8. ✅ Commit

---

## Testing Strategy

After each extraction:
```bash
# Quick smoke test
pytest tests/api/test_health.py -v

# Full API tests
pytest tests/api/ -v

# Ensure all routers still work
curl http://localhost:8000/health
curl http://localhost:8000/api/status
```

---

## Risks & Mitigation

### Risk 1: Breaking existing imports
**Mitigation:** Keep backward compatibility with `__all__` exports

### Risk 2: Middleware order changes
**Mitigation:** Document order in middleware_config.py with numbered comments

### Risk 3: Settings injection issues
**Mitigation:** Pass settings explicitly to all config functions

---

## Success Criteria

- ✅ main.py < 100 lines (target: <50)
- ✅ All tests passing (no regressions)
- ✅ Clear separation of concerns (each file = 1 responsibility)
- ✅ Factory pattern implemented (testable app creation)
- ✅ Documentation updated

---

**Estimated Time:** 60-90 minutes
**Difficulty:** Medium (refactoring existing working code)
**Risk:** Low (comprehensive test suite protects against regressions)
