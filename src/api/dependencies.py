"""
API Dependencies
Week 6 Day 4

Dependency injection for FastAPI endpoints.
Implements singleton pattern for expensive resources.
"""

from fastapi import Header, HTTPException, status
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

from .config import get_settings, load_production_api_keys
from ..orchestration.langgraph_orchestrator import LangGraphOrchestrator
from ..storage.timescale_store import TimescaleDBStore
from ..graph.neo4j_client import Neo4jClient
from ..vector_store.chroma_client import ChromaDBClient

logger = logging.getLogger(__name__)

# ============================================================================
# Singleton Instances
# ============================================================================

_orchestrator: Optional[LangGraphOrchestrator] = None
_timescale_store: Optional[TimescaleDBStore] = None
_neo4j_client: Optional[Neo4jClient] = None
_chromadb_client: Optional[ChromaDBClient] = None

# Rate limiting store (in-memory, replace with Redis in production)
_rate_limit_store: Dict[str, List[datetime]] = {}


# ============================================================================
# Resource Management
# ============================================================================

def get_orchestrator() -> LangGraphOrchestrator:
    """Get or create orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        logger.info("Initializing LangGraph Orchestrator...")
        _orchestrator = LangGraphOrchestrator()
        logger.info("✅ Orchestrator ready")
    return _orchestrator


def get_timescale_store() -> TimescaleDBStore:
    """Get or create TimescaleDB store singleton."""
    global _timescale_store
    if _timescale_store is None:
        logger.info("Connecting to TimescaleDB...")
        settings = get_settings()
        _timescale_store = TimescaleDBStore()  # Uses env vars
        logger.info("✅ TimescaleDB connected")
    return _timescale_store


def get_neo4j_client() -> Neo4jClient:
    """Get or create Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        logger.info("Connecting to Neo4j...")
        settings = get_settings()
        _neo4j_client = Neo4jClient()  # Uses env vars
        logger.info("✅ Neo4j connected")
    return _neo4j_client


def get_chromadb_client() -> ChromaDBClient:
    """Get or create ChromaDB client singleton."""
    global _chromadb_client
    if _chromadb_client is None:
        logger.info("Initializing ChromaDB...")
        _chromadb_client = ChromaDBClient()
        logger.info("✅ ChromaDB ready")
    return _chromadb_client


def cleanup_resources():
    """Cleanup all singleton resources on shutdown."""
    global _orchestrator, _timescale_store, _neo4j_client, _chromadb_client

    logger.info("Cleaning up resources...")

    if _timescale_store:
        try:
            _timescale_store.close()
        except Exception as e:
            logger.error(f"Error closing TimescaleDB: {e}")

    if _neo4j_client:
        try:
            _neo4j_client.close()
        except Exception as e:
            logger.error(f"Error closing Neo4j: {e}")

    _orchestrator = None
    _timescale_store = None
    _neo4j_client = None
    _chromadb_client = None

    logger.info("✅ Resources cleaned up")


# ============================================================================
# Authentication
# ============================================================================

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from X-API-Key header.

    Args:
        x_api_key: API key from header

    Returns:
        Validated API key

    Raises:
        HTTPException: If key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    settings = get_settings()

    # Merge configured keys with production keys from environment
    all_keys = {**settings.api_keys, **load_production_api_keys()}

    if x_api_key not in all_keys:
        logger.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    logger.debug(f"API key validated: {all_keys[x_api_key]['name']}")
    return x_api_key


# ============================================================================
# Rate Limiting
# ============================================================================

async def check_rate_limit(api_key: str) -> None:
    """
    Check rate limit for API key.

    Uses in-memory store. In production, replace with Redis.

    Args:
        api_key: Validated API key

    Raises:
        HTTPException: If rate limit exceeded
    """
    global _rate_limit_store

    settings = get_settings()
    all_keys = {**settings.api_keys, **load_production_api_keys()}

    now = datetime.utcnow()
    window = timedelta(hours=settings.rate_limit_window_hours)

    # Initialize if first request
    if api_key not in _rate_limit_store:
        _rate_limit_store[api_key] = []

    # Remove old entries outside window
    _rate_limit_store[api_key] = [
        ts for ts in _rate_limit_store[api_key]
        if now - ts < window
    ]

    # Check limit
    limit = all_keys[api_key].get("rate_limit", settings.default_rate_limit)
    current_count = len(_rate_limit_store[api_key])

    if current_count >= limit:
        logger.warning(f"Rate limit exceeded for {all_keys[api_key]['name']}: {current_count}/{limit}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} requests per {settings.rate_limit_window_hours} hour(s)",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int((now + window).timestamp()))
            }
        )

    # Add current request
    _rate_limit_store[api_key].append(now)

    logger.debug(f"Rate limit check passed: {current_count + 1}/{limit}")


async def verify_and_rate_limit(api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Combined authentication and rate limiting dependency.

    Args:
        api_key: API key from header

    Returns:
        Validated API key

    Raises:
        HTTPException: If auth fails or rate limit exceeded
    """
    # Verify API key
    validated_key = await verify_api_key(api_key)

    # Check rate limit
    await check_rate_limit(validated_key)

    return validated_key


# ============================================================================
# Health Checks
# ============================================================================

async def check_component_health() -> Dict[str, str]:
    """
    Check health of all components.

    Returns:
        Dict with component names and health status
    """
    health = {
        "api": "healthy",
        "orchestrator": "unknown",
        "timescaledb": "unknown",
        "neo4j": "unknown",
        "chromadb": "unknown"
    }

    # Check orchestrator
    try:
        if _orchestrator is not None:
            health["orchestrator"] = "healthy"
    except Exception as e:
        logger.error(f"Orchestrator health check failed: {e}")
        health["orchestrator"] = "unhealthy"

    # Check TimescaleDB
    try:
        if _timescale_store is not None:
            # TODO: Add actual health check query
            health["timescaledb"] = "healthy"
    except Exception as e:
        logger.error(f"TimescaleDB health check failed: {e}")
        health["timescaledb"] = "unhealthy"

    # Check Neo4j
    try:
        if _neo4j_client is not None:
            # TODO: Add actual health check query
            health["neo4j"] = "healthy"
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        health["neo4j"] = "unhealthy"

    # Check ChromaDB
    try:
        if _chromadb_client is not None:
            health["chromadb"] = "healthy"
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        health["chromadb"] = "unhealthy"

    return health
