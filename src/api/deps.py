"""Shared dependencies for FastAPI.

Week 12: Dependency injection for clean architecture
"""

from typing import Optional, Generator
import logging

from fastapi import Header, HTTPException, status

from .config import get_settings, load_production_api_keys
from ..storage.timescale_store import TimescaleDBStore
from ..graph.neo4j_client import Neo4jClient
from ..orchestration.langgraph_orchestrator import LangGraphOrchestrator

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton instances
_orchestrator: Optional[LangGraphOrchestrator] = None
_timescale_store: Optional[TimescaleDBStore] = None
_neo4j_client: Optional[Neo4jClient] = None


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header."
        )
    
    api_keys = {**settings.api_keys, **load_production_api_keys()}
    
    if x_api_key not in api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return x_api_key


def get_timescale_store() -> TimescaleDBStore:
    """Get TimescaleDB store (singleton)."""
    global _timescale_store
    if _timescale_store is None:
        _timescale_store = TimescaleDBStore(dsn=settings.timescaledb_url)
    return _timescale_store


def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client (singleton)."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
    return _neo4j_client


def get_orchestrator() -> LangGraphOrchestrator:
    """Get LangGraph orchestrator (singleton)."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LangGraphOrchestrator(
            openai_api_key=settings.openai_api_key,
            anthropic_api_key=settings.anthropic_api_key,
        )
    return _orchestrator
