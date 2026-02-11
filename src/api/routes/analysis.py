"""Analysis and query routes.

Week 12: Extracted from main.py God Object
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Header, Request
from starlette.responses import Response
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import uuid4
import logging
import asyncio
import os

from pydantic import BaseModel, Field, validator

from ...orchestration.langgraph_orchestrator import LangGraphOrchestrator, StateStatus
from ..config import get_settings
from ..security import input_validator
from ..metrics import queries_submitted_total
from ..query_tracker import create_query_status, update_query_status
from ..websocket import broadcast_completion, broadcast_error, broadcast_status_update

router = APIRouter(prefix="/api", tags=["Analysis"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Request/Response Models
class QueryRequest(BaseModel):
    """Request model for query execution."""
    query: str = Field(..., min_length=10, max_length=1000, description="Financial analysis query")
    priority: Optional[str] = Field("normal", description="Query priority: low, normal, high")
    provider: Optional[str] = Field("deepseek", description="LLM provider: deepseek, openai, gemini")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        validation = input_validator.validate_query(v)
        if not validation.is_valid:
            raise ValueError(f"Security validation failed: {validation.error_message}")
        return validation.sanitized_value
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high']:
            raise ValueError("Priority must be: low, normal, or high")
        return v

    @validator('provider')
    def validate_provider(cls, v):
        if v is None:
            return "deepseek"
        if v not in ['deepseek', 'openai', 'gemini']:
            raise ValueError("Provider must be: deepseek, openai, or gemini")
        return v


class QueryResponse(BaseModel):
    """Response model for query submission."""
    query_id: str = Field(..., description="Unique query identifier")
    status: str = Field(..., description="Query status")
    message: str = Field(..., description="Human-readable message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class CompareRequest(BaseModel):
    """Request model for multi-ticker comparative analysis."""
    query: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Comparative query. Use {ticker} placeholder optionally."
    )
    tickers: List[str] = Field(
        ...,
        min_items=2,
        max_items=10,
        description="Ticker symbols for comparison."
    )
    priority: Optional[str] = Field("normal", description="Query priority: low, normal, high")
    provider: Optional[str] = Field("deepseek", description="LLM provider: deepseek, openai, gemini")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        validation = input_validator.validate_query(v)
        if not validation.is_valid:
            raise ValueError(f"Security validation failed: {validation.error_message}")
        return validation.sanitized_value

    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high']:
            raise ValueError("Priority must be: low, normal, or high")
        return v

    @validator('provider')
    def validate_provider(cls, v):
        if v is None:
            return "deepseek"
        if v not in ['deepseek', 'openai', 'gemini']:
            raise ValueError("Provider must be: deepseek, openai, or gemini")
        return v

    @validator('tickers')
    def validate_tickers(cls, v):
        normalized = []
        for ticker in v:
            token = str(ticker).strip().upper()
            if token and token not in normalized:
                normalized.append(token)
        if len(normalized) < 2:
            raise ValueError("At least 2 unique tickers are required")
        return normalized


class AnalysisResponse(BaseModel):
    """Analysis result response."""
    query_id: str
    status: str
    answer: Optional[str] = None
    verified_fact: Optional[Dict] = None
    data_source: str = "yfinance"
    data_freshness: Optional[datetime] = None
    detected_language: Optional[str] = None
    verification_score: float = 0.0
    cost_usd: float = 0.0
    tokens_used: int = 0
    disclaimer: str = Field(
        default="This analysis is for informational purposes only..."
    )


class DebateResponse(AnalysisResponse):
    """Standalone debate response with full perspective details."""
    provider: str = "deepseek"
    debate_reports: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis: Optional[Dict[str, Any]] = None
    nodes_visited: List[str] = Field(default_factory=list)


class CompareTickerResult(BaseModel):
    """Per-ticker result in comparative analysis."""
    ticker: str
    query_id: str
    status: str
    detected_language: Optional[str] = None
    answer: Optional[str] = None
    verification_score: float = 0.0
    cost_usd: float = 0.0
    tokens_used: int = 0
    error: Optional[str] = None


class CompareResponse(BaseModel):
    """Aggregated response for multi-ticker comparative analysis."""
    compare_id: str
    status: str
    provider: str
    tickers: List[str]
    detected_language: Optional[str] = None
    results: List[CompareTickerResult]
    completed_count: int
    failed_count: int
    leader_ticker: Optional[str] = None
    average_verification_score: float = 0.0
    total_cost_usd: float = 0.0
    total_tokens_used: int = 0
    summary: str
    pipeline_path: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = Field(
        default="This analysis is for informational purposes only..."
    )


# Singleton orchestrator instance
_orchestrator: Optional[LangGraphOrchestrator] = None
_orchestrator_provider: Optional[str] = None


def get_orchestrator_instance() -> Dict[str, Any]:
    """Return current orchestrator singleton metadata without lazy creation."""
    return {
        "orchestrator": _orchestrator,
        "provider": _orchestrator_provider,
    }


def get_orchestrator(provider: Optional[str] = None) -> LangGraphOrchestrator:
    """Get or create LangGraph orchestrator."""
    global _orchestrator, _orchestrator_provider
    requested_provider = provider or settings.llm_provider

    async def _tracker_broadcast(
        query_id: str,
        status: str,
        current_node: Optional[str] = None,
        progress: float = 0.0,
        verified_facts_count: int = 0,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        state_from_node = {
            "PLAN": "planning",
            "FETCH": "fetching",
            "VEE": "executing",
            "GATE": "validating",
            "DEBATE": "debating",
            "ERROR": "failed",
        }
        normalized_status = status
        if status == "processing":
            normalized_status = state_from_node.get(str(current_node or "").upper(), "pending")
        elif status == "accepted":
            normalized_status = "pending"
        elif status not in {"completed", "failed"}:
            normalized_status = "pending"

        update_query_status(
            query_id=query_id,
            status=normalized_status,
            current_node=current_node,
            progress=progress,
            verified_facts_count=verified_facts_count,
            error=error,
            metadata=metadata,
        )
        try:
            await broadcast_status_update(
                query_id=query_id,
                status=normalized_status,
                progress=progress,
                current_step=str(current_node or ""),
            )
            if normalized_status == "completed":
                await broadcast_completion(
                    query_id=query_id,
                    result_summary={
                        "verified_facts_count": verified_facts_count,
                        "metadata": metadata or {},
                    },
                )
            elif normalized_status == "failed" and error:
                await broadcast_error(query_id=query_id, error=str(error))
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast skipped for {query_id}: {ws_err}")

    if _orchestrator is None or _orchestrator_provider != requested_provider:
        _orchestrator = LangGraphOrchestrator(
            claude_api_key=settings.anthropic_api_key,
            llm_provider=requested_provider,
            use_real_llm=True,
            broadcast_callback=_tracker_broadcast,
        )
        _orchestrator_provider = requested_provider
    return _orchestrator


def _validate_provider_key(provider: str):
    """Fail closed when provider credentials are missing."""
    provider_env_var = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    env_var = provider_env_var[provider]
    if not os.getenv(env_var):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{env_var} is required for provider '{provider}'"
        )


def _detect_language(query: str) -> str:
    """Detect query language using lightweight script heuristics."""
    if not query:
        return "unknown"
    cyrillic_count = len(__import__("re").findall(r"[А-Яа-яЁё]", query))
    latin_count = len(__import__("re").findall(r"[A-Za-z]", query))
    if cyrillic_count == 0 and latin_count == 0:
        return "unknown"
    if cyrillic_count > latin_count:
        return "ru"
    if latin_count > cyrillic_count:
        return "en"
    return "unknown"


@router.post("/analyze", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    raw_request: Request,
    x_api_key: Optional[str] = Header(None),
    http_response: Response = None  # FastAPI Response for setting headers
):
    """
    Analyze financial query with full verification pipeline.
    
    Flow: Query → Router → LLM/Debate → Truth Boundary → Response
    
    Week 10: Added route-level caching for performance
    """
    from ..cache_simple import analyze_cache, generate_cache_key, get_cached_response, set_cached_response
    
    detected_language = _detect_language(request.query)

    # Generate cache key
    cache_key = generate_cache_key(raw_request, request.dict())
    
    # Check cache first (FAST PATH)
    if settings.cache_enabled:
        try:
            cached = await get_cached_response(cache_key)
            if cached:
                logger.info(f"Cache HIT for query: {request.query[:50]}...")
                # Set cache headers
                if http_response:
                    http_response.headers["X-Cache"] = "HIT"
                    http_response.headers["X-Cache-Key"] = cache_key[:16]
                # Return cached response with metadata
                return AnalysisResponse(**cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    
    # SLOW PATH: Process query
    query_id = str(uuid4())
    
    # Track metrics
    queries_submitted_total.labels(priority="normal").inc()
    
    logger.info(f"Query {query_id}: {request.query[:50]}... (Cache MISS)")
    
    try:
        # Get orchestrator
        orchestrator = get_orchestrator(request.provider)
        
        # Process query (async)
        result = await orchestrator.process_query_async(
            query_id=query_id,
            query_text=request.query,
            provider=request.provider,
            context={"priority": request.priority}
        )
        
        # Build response model
        result_response = AnalysisResponse(
            query_id=query_id,
            status="completed",
            answer=result.get("answer"),
            verified_fact=result.get("verified_fact"),
            data_source=result.get("data_source", "yfinance"),
            data_freshness=result.get("data_freshness"),
            detected_language=detected_language,
            verification_score=result.get("verification_score", 0.0),
            cost_usd=result.get("cost_usd", 0.0),
            tokens_used=result.get("tokens_used", 0)
        )
        
        # Cache the response
        if settings.cache_enabled:
            try:
                await set_cached_response(
                    cache_key,
                    result_response.dict(),
                    ttl_seconds=settings.cache_ttl_seconds
                )
                logger.info(f"Cached response for: {request.query[:50]}...")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")

        # Set cache miss headers
        if http_response:
            http_response.headers["X-Cache"] = "MISS"
            http_response.headers["X-Cache-Key"] = cache_key[:16]

        return result_response
        
    except Exception as e:
        logger.error(f"Query {query_id} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None)
):
    """
    Submit query for async processing.
    
    Returns immediately with query_id. Check status via /api/status/{query_id}
    """
    query_id = str(uuid4())
    detected_language = _detect_language(request.query)
    
    queries_submitted_total.labels(priority="normal").inc()

    create_query_status(
        query_id=query_id,
        query_text=request.query,
        status="accepted",
        progress=0.0,
        metadata={
            "priority": request.priority,
            "provider": request.provider,
            "detected_language": detected_language,
            "pipeline_path": "langgraph",
            "queued_via": "fastapi_background_task",
        },
    )

    async def _run_query_in_background():
        try:
            update_query_status(
                query_id=query_id,
                status="processing",
                current_node="PLAN",
                progress=0.05,
            )

            orchestrator = get_orchestrator(request.provider)
            result = await orchestrator.process_query_async(
                query_id=query_id,
                query_text=request.query,
                provider=request.provider,
                context={"priority": request.priority, "mode": "async_query"},
            )
            is_completed = result.get("status") == "completed"
            update_query_status(
                query_id=query_id,
                status="completed" if is_completed else "failed",
                current_node=None,
                progress=1.0 if is_completed else 0.0,
                verified_facts_count=1 if result.get("verified_fact") else 0,
                error=result.get("error"),
                metadata={
                    "answer": result.get("answer"),
                    "episode_id": result.get("episode_id"),
                    "detected_language": detected_language,
                    "verification_score": result.get("verification_score"),
                    "nodes_visited": result.get("nodes_visited", []),
                },
            )
        except Exception as e:
            logger.error(f"Async query {query_id} failed: {e}")
            update_query_status(
                query_id=query_id,
                status="failed",
                current_node="ERROR",
                progress=0.0,
                error=str(e),
            )

    # Fire-and-forget worker: keep /api/query low-latency.
    asyncio.create_task(_run_query_in_background())
    
    return QueryResponse(
        query_id=query_id,
        status="accepted",
        message="Query accepted for processing",
        estimated_completion=datetime.utcnow() + timedelta(seconds=30)
    )


@router.post("/debate", response_model=DebateResponse)
async def debate_query(
    request: QueryRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Run multi-LLM debate on complex query.
    
    Uses Proposer (DeepSeek) + Critic (Claude) + Judge (GPT-4o)
    """
    query_id = str(uuid4())
    detected_language = _detect_language(request.query)
    
    logger.info(f"Debate {query_id}: {request.query[:50]}...")
    
    queries_submitted_total.labels(priority=request.priority).inc()

    try:
        _validate_provider_key(request.provider)
        orchestrator = get_orchestrator(request.provider)

        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(
            None,
            orchestrator.run,
            query_id,
            request.query,
            None,
            True
        )

        if final_state.status != StateStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Debate failed: {final_state.error_message or 'pipeline did not complete'}"
            )

        debate_reports: List[Dict[str, Any]] = []
        for report in final_state.debate_reports or []:
            if hasattr(report, "model_dump"):
                debate_reports.append(report.model_dump())
            elif hasattr(report, "dict"):
                debate_reports.append(report.dict())
            else:
                debate_reports.append({"raw": str(report)})

        synthesis_payload: Optional[Dict[str, Any]] = None
        if final_state.synthesis:
            if hasattr(final_state.synthesis, "model_dump"):
                synthesis_payload = final_state.synthesis.model_dump()
            elif hasattr(final_state.synthesis, "dict"):
                synthesis_payload = final_state.synthesis.dict()
            else:
                synthesis_payload = {"raw": str(final_state.synthesis)}

        verified_fact_payload: Optional[Dict[str, Any]] = None
        if final_state.verified_fact:
            fact = final_state.verified_fact
            verified_fact_payload = {
                "fact_id": fact.fact_id,
                "statement": fact.statement or str(fact.extracted_values),
                "confidence_score": fact.confidence_score,
                "source": fact.data_source
            }

        stats = {}
        if getattr(orchestrator, "debate_adapter", None):
            stats = orchestrator.debate_adapter.get_stats() or {}

        return DebateResponse(
            query_id=query_id,
            status="debate_completed",
            provider=request.provider,
            detected_language=detected_language,
            answer=(
                synthesis_payload.get("balanced_view")
                if synthesis_payload else "Debate completed"
            ),
            verified_fact=verified_fact_payload,
            verification_score=(
                final_state.verified_fact.confidence_score
                if final_state.verified_fact else 0.0
            ),
            cost_usd=float(stats.get("total_cost", 0.0)),
            tokens_used=int(
                stats.get("total_input_tokens", 0)
                + stats.get("total_output_tokens", 0)
            ),
            debate_reports=debate_reports,
            synthesis=synthesis_payload,
            nodes_visited=final_state.nodes_visited or []
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Debate {query_id} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debate failed: {str(e)}"
        )


@router.post("/compare", response_model=CompareResponse, status_code=status.HTTP_200_OK)
async def compare_tickers(
    request: CompareRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Run parallel comparative analysis for multiple tickers through LangGraph.

    Production path is unified with /api/analyze (same orchestrator pipeline).
    """
    compare_id = str(uuid4())
    detected_language = _detect_language(request.query)
    logger.info(f"Compare {compare_id}: {request.tickers} via {request.provider}")

    queries_submitted_total.labels(priority=request.priority).inc()
    _validate_provider_key(request.provider)
    orchestrator = get_orchestrator(request.provider)

    async def _run_ticker(ticker: str) -> CompareTickerResult:
        query_id = str(uuid4())
        if "{ticker}" in request.query:
            ticker_query = request.query.replace("{ticker}", ticker)
        else:
            ticker_query = f"{request.query} for {ticker}"

        try:
            result = await orchestrator.process_query_async(
                query_id=query_id,
                query_text=ticker_query,
                provider=request.provider,
                context={
                    "priority": request.priority,
                    "compare_id": compare_id,
                    "ticker": ticker,
                    "mode": "multi_ticker_compare",
                },
            )
            return CompareTickerResult(
                ticker=ticker,
                query_id=query_id,
                status=result.get("status", "completed"),
                detected_language=detected_language,
                answer=result.get("answer"),
                verification_score=float(result.get("verification_score", 0.0) or 0.0),
                cost_usd=float(result.get("cost_usd", 0.0) or 0.0),
                tokens_used=int(result.get("tokens_used", 0) or 0),
                error=result.get("error"),
            )
        except Exception as e:
            logger.error(f"Compare {compare_id}: ticker {ticker} failed: {e}")
            return CompareTickerResult(
                ticker=ticker,
                query_id=query_id,
                status="failed",
                detected_language=detected_language,
                error=str(e),
            )

    results = await asyncio.gather(*[_run_ticker(t) for t in request.tickers])

    completed = [r for r in results if r.status == "completed"]
    failed = [r for r in results if r.status != "completed"]

    overall_status = "completed"
    if completed and failed:
        overall_status = "partial_failed"
    elif failed and not completed:
        overall_status = "failed"

    leader_ticker = None
    average_score = 0.0
    if completed:
        leader = max(completed, key=lambda item: item.verification_score)
        leader_ticker = leader.ticker
        average_score = sum(r.verification_score for r in completed) / len(completed)

    total_cost = sum(r.cost_usd for r in results)
    total_tokens = sum(r.tokens_used for r in results)

    summary = (
        f"Compared {len(request.tickers)} tickers: "
        f"{len(completed)} completed, {len(failed)} failed."
    )
    if leader_ticker:
        summary += f" Highest verification score: {leader_ticker}."

    return CompareResponse(
        compare_id=compare_id,
        status=overall_status,
        provider=request.provider,
        tickers=request.tickers,
        detected_language=detected_language,
        results=results,
        completed_count=len(completed),
        failed_count=len(failed),
        leader_ticker=leader_ticker,
        average_verification_score=round(average_score, 6),
        total_cost_usd=round(total_cost, 6),
        total_tokens_used=total_tokens,
        summary=summary,
        pipeline_path={
            "production_path": "langgraph",
            "bypasses": [],
            "notes": "Runs /api/analyze-equivalent pipeline per ticker in parallel.",
        },
    )


# ============================================================================
# Multi-LLM Debate Endpoint (Week 12+)
# ============================================================================

class MultiLLMDebateRequest(BaseModel):
    """Request model for multi-LLM debate."""
    query: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Financial analysis query"
    )
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context (price, metrics, etc.)"
    )

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        validation = input_validator.validate_query(v)
        if not validation.is_valid:
            raise ValueError(f"Security validation failed: {validation.error_message}")
        return validation.sanitized_value


class MultiLLMDebateResponse(BaseModel):
    """Response model for multi-LLM debate."""
    perspectives: Dict[str, Any] = Field(
        ...,
        description="Bull/Bear/Arbiter perspectives"
    )
    synthesis: Dict[str, Any] = Field(
        ...,
        description="Synthesis with recommendation"
    )
    metadata: Dict[str, Any] = Field(
        ...,
        description="Cost, latency, timestamp"
    )


@router.post("/analyze-debate", response_model=MultiLLMDebateResponse, status_code=status.HTTP_200_OK)
async def analyze_multi_llm_debate(
    request: MultiLLMDebateRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Run multi-LLM debate with parallel Bull/Bear/Arbiter agents.

    **New Feature:** Week 12+ commercial value feature.

    **Architecture:**
    - Bull Agent: DeepSeek (optimistic, fast & cheap)
    - Bear Agent: Claude (skeptical, critical thinking)
    - Arbiter Agent: GPT-4 (balanced synthesis)

    **Performance:**
    - Response time: ~3-4s (parallel execution)
    - Cost: ~$0.002 per query

    **Returns:**
    - 3 perspectives (bull/bear/arbiter)
    - Final recommendation (BUY/HOLD/SELL)
    - Overall confidence score
    - Risk/reward ratio
    """
    try:
        logger.info(f"Multi-LLM debate request: {request.query[:100]}...")

        # Import orchestrator (lazy import to avoid import errors if packages missing)
        from ...debate.parallel_orchestrator import run_multi_llm_debate

        # Run debate
        result = await run_multi_llm_debate(
            query=request.query,
            context=request.context
        )

        logger.info(
            f"Multi-LLM debate complete: {result['metadata']['latency_ms']:.0f}ms, "
            f"Recommendation: {result['synthesis']['recommendation']}"
        )

        return MultiLLMDebateResponse(**result)

    except ImportError as e:
        logger.error(f"Multi-LLM debate: Missing dependencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Multi-LLM debate requires additional packages. "
                "Install: pip install openai anthropic"
            )
        )
    except ValueError as e:
        logger.error(f"Multi-LLM debate: Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Multi-LLM debate: Missing API keys. "
                "Set: DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY"
            )
        )
    except Exception as e:
        logger.error(f"Multi-LLM debate failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-LLM debate failed: {str(e)}"
        )
