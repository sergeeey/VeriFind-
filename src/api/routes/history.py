"""Query history API routes."""

from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query, status

from ...storage.query_history_store import QueryHistoryStore
from ..config import get_settings

router = APIRouter(prefix="/api/history", tags=["History"])
logger = logging.getLogger(__name__)
settings = get_settings()

_history_store: Optional[QueryHistoryStore] = None


def get_history_store() -> QueryHistoryStore:
    """Get query history store singleton."""
    global _history_store
    if _history_store is None:
        _history_store = QueryHistoryStore(settings.timescaledb_url)
    return _history_store


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_history(
    q: str = Query(..., min_length=1, description="Search phrase"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search query history by text."""
    try:
        store = get_history_store()
        return store.search_history(search_query=q, limit=limit)
    except Exception as e:
        logger.warning(f"History search failed: {e}")
        return []


@router.get("", response_model=List[Dict[str, Any]])
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    ticker: Optional[str] = Query(None, min_length=1, max_length=10),
):
    """List recent query history entries."""
    try:
        store = get_history_store()
        return store.get_history(limit=limit, ticker=ticker)
    except Exception as e:
        logger.warning(f"History fetch failed: {e}")
        return []


@router.get("/{query_id}", response_model=Dict[str, Any])
async def get_history_entry(query_id: str):
    """Get single query history entry by query ID."""
    try:
        store = get_history_store()
        entry = store.get_entry(query_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"History entry {query_id} not found",
            )
        return entry
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"History entry fetch failed for {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve history entry",
        )


@router.delete("/{query_id}", response_model=Dict[str, Any])
async def delete_history_entry(query_id: str):
    """Delete single query history entry by query ID."""
    try:
        store = get_history_store()
        deleted = store.delete_entry(query_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"History entry {query_id} not found",
            )
        return {"deleted": True, "query_id": query_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"History delete failed for {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete history entry",
        )
