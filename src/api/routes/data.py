"""Data retrieval routes (facts, episodes, status).

Week 12: Extracted from main.py God Object
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import pandas as pd
import yfinance as yf

from pydantic import BaseModel, Field

from ...storage.timescale_store import TimescaleDBStore
from ...graph.neo4j_client import Neo4jClient
from ..config import get_settings
from ..query_tracker import (
    get_query_status as get_tracked_query_status,
    list_query_statuses as list_tracked_query_statuses,
)

router = APIRouter(prefix="/api", tags=["Data"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_status_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return datetime.utcnow()
    return datetime.utcnow()

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


class ChartPoint(BaseModel):
    """OHLC point with optional indicators."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    ema: Optional[float] = None
    rsi: Optional[float] = None


class ChartDataResponse(BaseModel):
    """Advanced chart data response."""
    ticker: str
    period: str
    interval: str
    points: List[ChartPoint]
    point_count: int
    indicators: Dict[str, Any] = Field(default_factory=dict)
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
    query_text: Optional[str] = None
    status: str
    state: str
    current_node: Optional[str] = None
    episode_id: Optional[str] = None
    progress: float = Field(..., ge=0.0, le=1.0, description="Completion progress (0.0-1.0)")
    verified_facts_count: int = Field(0, description="Number of verified facts generated")
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StatusSummaryResponse(BaseModel):
    total_tracked: int
    completed: int
    failed: int
    pending: int
    today_count: int
    avg_completion_ms: Optional[float] = None


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
    tracked = get_tracked_query_status(query_id)
    if not tracked:
        now = datetime.utcnow()
        return StatusResponse(
            query_id=query_id,
            query_text=None,
            status="unknown",
            state="pending",
            progress=0.0,
            verified_facts_count=0,
            episode_id=None,
            created_at=now,
            updated_at=now,
            metadata={
                "message": "Query ID not found in tracker. Submit via /api/query first.",
            },
        )

    def _parse(value: Any) -> datetime:
        return _parse_status_datetime(value)

    normalized_status = str(tracked.get("status", "unknown"))
    return StatusResponse(
        query_id=query_id,
        query_text=tracked.get("query_text"),
        status=normalized_status,
        state=normalized_status,
        current_node=tracked.get("current_node"),
        episode_id=(
            tracked.get("episode_id")
            or (tracked.get("metadata", {}) or {}).get("episode_id")
        ),
        progress=float(tracked.get("progress", 0.0)),
        verified_facts_count=int(tracked.get("verified_facts_count", 0)),
        error=tracked.get("error"),
        created_at=_parse(tracked.get("created_at")),
        updated_at=_parse(tracked.get("updated_at")),
        metadata=tracked.get("metadata", {}) or {},
    )


@router.get("/status", response_model=List[StatusResponse])
async def list_query_statuses(
    limit: int = Query(20, ge=1, le=200),
    state: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
):
    """List recently tracked query statuses (latest first)."""
    rows = list_tracked_query_statuses(limit=limit, state=state, query_contains=query)
    items: List[StatusResponse] = []
    for row in rows:
        normalized_status = str(row.get("status", "unknown"))
        items.append(
            StatusResponse(
                query_id=str(row.get("query_id", "")),
                query_text=row.get("query_text"),
                status=normalized_status,
                state=normalized_status,
                current_node=row.get("current_node"),
                episode_id=(
                    row.get("episode_id")
                    or (row.get("metadata", {}) or {}).get("episode_id")
                ),
                progress=float(row.get("progress", 0.0)),
                verified_facts_count=int(row.get("verified_facts_count", 0)),
                error=row.get("error"),
                created_at=_parse_status_datetime(row.get("created_at")),
                updated_at=_parse_status_datetime(row.get("updated_at")),
                metadata=row.get("metadata", {}) or {},
            )
        )
    return items


@router.get("/status-summary", response_model=StatusSummaryResponse)
async def get_status_summary():
    """Aggregate status metrics for dashboard widgets."""
    rows = list_tracked_query_statuses(limit=200)
    total = len(rows)
    completed_rows = [row for row in rows if str(row.get("status", "")).lower() == "completed"]
    failed_rows = [row for row in rows if str(row.get("status", "")).lower() == "failed"]
    pending_rows = [row for row in rows if str(row.get("status", "")).lower() in {"pending", "planning", "fetching", "executing", "validating", "debating"}]

    today = datetime.utcnow().date().isoformat()
    today_count = sum(
        1 for row in rows if str(row.get("created_at", "")).startswith(today)
    )

    durations_ms: List[float] = []
    for row in completed_rows:
        created_at = _parse_status_datetime(row.get("created_at"))
        updated_at = _parse_status_datetime(row.get("updated_at"))
        if updated_at >= created_at:
            durations_ms.append((updated_at - created_at).total_seconds() * 1000.0)

    avg_completion_ms = None
    if durations_ms:
        avg_completion_ms = sum(durations_ms) / len(durations_ms)

    return StatusSummaryResponse(
        total_tracked=total,
        completed=len(completed_rows),
        failed=len(failed_rows),
        pending=len(pending_rows),
        today_count=today_count,
        avg_completion_ms=avg_completion_ms,
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


def _compute_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI indicator."""
    delta = close_series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi


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


@router.get("/data/chart/{ticker}", response_model=ChartDataResponse)
async def get_advanced_chart_data(
    ticker: str,
    period: str = Query("6mo", pattern="^(1mo|3mo|6mo|1y|2y|5y|max)$"),
    interval: str = Query("1d", pattern="^(1d|1wk|1mo)$"),
    ema_period: int = Query(20, ge=2, le=200),
    rsi_period: int = Query(14, ge=2, le=100),
    include_volume: bool = Query(True),
):
    """
    Get OHLC chart data with technical indicators for frontend charting.
    """
    token = ticker.strip().upper()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ticker is required",
        )

    try:
        frame = yf.Ticker(token).history(period=period, interval=interval, auto_adjust=True)
        if frame.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No chart data available for {token}",
            )

        frame = frame.copy()
        frame["EMA"] = frame["Close"].ewm(span=ema_period, adjust=False).mean()
        frame["RSI"] = _compute_rsi(frame["Close"], period=rsi_period)

        points: List[ChartPoint] = []
        for index, row in frame.iterrows():
            point = ChartPoint(
                timestamp=index.isoformat(),
                open=round(float(row["Open"]), 6),
                high=round(float(row["High"]), 6),
                low=round(float(row["Low"]), 6),
                close=round(float(row["Close"]), 6),
                volume=(int(row["Volume"]) if include_volume and pd.notna(row.get("Volume")) else None),
                ema=(round(float(row["EMA"]), 6) if pd.notna(row.get("EMA")) else None),
                rsi=(round(float(row["RSI"]), 6) if pd.notna(row.get("RSI")) else None),
            )
            points.append(point)

        return ChartDataResponse(
            ticker=token,
            period=period,
            interval=interval,
            points=points,
            point_count=len(points),
            indicators={
                "ema_period": ema_period,
                "rsi_period": rsi_period,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chart data for {token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chart data",
        )
