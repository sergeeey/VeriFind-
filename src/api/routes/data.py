"""Data retrieval routes (facts, episodes, status).

Week 12: Extracted from main.py God Object
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from pydantic import BaseModel, Field

from ...storage.timescale_store import TimescaleDBStore
from ...graph.neo4j_client import Neo4jClient
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["Data"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Response Models
class DataTickersResponse(BaseModel):
    """Response for data tickers endpoint."""
    tickers: List[str]
    disclaimer: str = Field(default="This analysis is for informational purposes only...")


class DataFetchResponse(BaseModel):
    """Response for data fetch endpoint."""
    task_id: str
    status: str
    message: str
    disclaimer: str = Field(default="This analysis is for informational purposes only...")


class VerifiedFactResponse(BaseModel):
    """Response model for verified fact."""
    fact_id: str
    query_id: str
    statement: str
    value: Optional[float] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    source_code: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_source: str = Field(default="yfinance")
    data_freshness: Optional[datetime] = None
    disclaimer: str = Field(
        default="This analysis is for informational purposes only..."
    )


class StatusResponse(BaseModel):
    """Response model for query status."""
    query_id: str
    status: str
    current_node: Optional[str] = None
    progress: float = Field(..., ge=0.0, le=1.0, description="Completion progress (0.0-1.0)")
    verified_facts_count: int = Field(0, description="Number of verified facts generated")
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EpisodeResponse(BaseModel):
    """Response model for episode details."""
    episode_id: str
    query_id: str
    query_text: str
    status: str
    verified_facts: List[VerifiedFactResponse]
    synthesis: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None


# Store instances (TODO: replace with proper dependency injection)
_db_store: Optional[TimescaleDBStore] = None
_graph_client: Optional[Neo4jClient] = None


def get_db_store() -> TimescaleDBStore:
    """Get TimescaleDB store instance."""
    global _db_store
    if _db_store is None:
        _db_store = TimescaleDBStore(
            dsn=settings.timescaledb_url
        )
    return _db_store


def get_graph_client() -> Neo4jClient:
    """Get Neo4j client instance."""
    global _graph_client
    if _graph_client is None:
        _graph_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
    return _graph_client


@router.get("/status/{query_id}", response_model=StatusResponse)
async def get_query_status(query_id: str):
    """Get query execution status."""
    # TODO: Implement actual status tracking
    return StatusResponse(
        query_id=query_id,
        status="completed",
        progress=1.0,
        verified_facts_count=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@router.get("/facts", response_model=List[VerifiedFactResponse])
async def list_facts(
    query: Optional[str] = Query(None, description="Filter by query text"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List verified facts with pagination."""
    try:
        store = get_db_store()
        facts = await store.list_facts(
            query_filter=query,
            limit=limit,
            offset=offset
        )
        return [VerifiedFactResponse(**fact) for fact in facts]
    except Exception as e:
        logger.error(f"Failed to list facts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve facts"
        )


@router.get("/facts/{fact_id}", response_model=VerifiedFactResponse)
async def get_fact(fact_id: str):
    """Get specific verified fact by ID."""
    try:
        store = get_db_store()
        fact = await store.get_fact(fact_id)
        if not fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fact {fact_id} not found"
            )
        return VerifiedFactResponse(**fact)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fact {fact_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fact"
        )


@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str):
    """Get episode details with all verified facts."""
    try:
        graph = get_graph_client()
        episode = graph.get_episode(episode_id)
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        return EpisodeResponse(**episode)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get episode {episode_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve episode"
        )


@router.get("/episodes", response_model=List[Dict[str, Any]])
async def list_episodes(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List episodes with pagination."""
    try:
        graph = get_graph_client()
        episodes = graph.list_episodes(limit=limit, offset=offset)
        return episodes
    except Exception as e:
        logger.error(f"Failed to list episodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve episodes"
        )


@router.get("/graph/facts", response_model=List[Dict[str, Any]])
async def get_graph_facts(
    ticker: str = Query(..., min_length=1, description="Ticker symbol, e.g. AAPL"),
    limit: int = Query(20, ge=1, le=200)
):
    """Search graph facts related to ticker."""
    try:
        graph = get_graph_client()
        return graph.search_facts_by_ticker(ticker=ticker, limit=limit)
    except Exception as e:
        logger.error(f"Failed to search graph facts for ticker {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search graph facts"
        )


@router.get("/graph/lineage/{fact_id}", response_model=Dict[str, Any])
async def get_graph_lineage(fact_id: str):
    """Get lineage for a fact."""
    try:
        graph = get_graph_client()
        fact = graph.get_fact_node(fact_id)
        if not fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fact {fact_id} not found"
            )
        lineage = graph.get_fact_lineage(fact_id)
        return {
            "fact_id": fact_id,
            "fact": fact,
            "ancestors": lineage,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lineage for fact {fact_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fact lineage"
        )


@router.get("/graph/related/{fact_id}", response_model=Dict[str, Any])
async def get_graph_related(fact_id: str):
    """Get related facts and synthesis artifacts for a fact."""
    try:
        graph = get_graph_client()
        related = graph.get_related_facts(fact_id)
        if not related.get("fact"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fact {fact_id} not found"
            )
        return related
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get related artifacts for fact {fact_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve related facts"
        )


@router.get("/graph/stats", response_model=Dict[str, int])
async def get_graph_stats():
    """Get Neo4j graph statistics."""
    try:
        graph = get_graph_client()
        return graph.get_graph_stats()
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve graph stats"
        )


# =============================================================================
# Data API Endpoints
# =============================================================================

@router.get("/data/tickers", response_model=DataTickersResponse)
async def get_data_tickers():
    """
    Get list of available tickers for market data.
    
    Returns:
        List of ticker symbols
    """
    # Return popular tickers as default
    default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM"]
    return DataTickersResponse(tickers=default_tickers)


class FetchRequest(BaseModel):
    """Request model for data fetch."""
    ticker: str
    start_date: str
    end_date: str


@router.post("/data/fetch", response_model=DataFetchResponse, status_code=status.HTTP_202_ACCEPTED)
async def fetch_market_data(request: FetchRequest):
    """
    Fetch market data for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        Task ID for tracking fetch progress
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    # In production, this would queue a background task
    logger.info(f"Data fetch requested for {request.ticker} from {request.start_date} to {request.end_date}")
    
    return DataFetchResponse(
        task_id=task_id,
        status="accepted",
        message=f"Data fetch for {request.ticker} has been queued"
    )
