"""Analysis and query routes.

Week 12: Extracted from main.py God Object
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Header
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
import logging

from pydantic import BaseModel, Field, validator

from ...orchestration.langgraph_orchestrator import LangGraphOrchestrator
from ...truth_boundary.gate import VerifiedFact
from ..config import get_settings
from ..security import input_validator
from ..metrics import queries_submitted_total

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


class QueryResponse(BaseModel):
    """Response model for query submission."""
    query_id: str = Field(..., description="Unique query identifier")
    status: str = Field(..., description="Query status")
    message: str = Field(..., description="Human-readable message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class AnalysisResponse(BaseModel):
    """Analysis result response."""
    query_id: str
    status: str
    answer: Optional[str] = None
    verified_fact: Optional[Dict] = None
    data_source: str = "yfinance"
    data_freshness: Optional[datetime] = None
    verification_score: float = 0.0
    cost_usd: float = 0.0
    tokens_used: int = 0
    disclaimer: str = Field(
        default="This analysis is for informational purposes only..."
    )


# Singleton orchestrator instance
_orchestrator: Optional[LangGraphOrchestrator] = None

def get_orchestrator() -> LangGraphOrchestrator:
    """Get or create LangGraph orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LangGraphOrchestrator(
            claude_api_key=settings.anthropic_api_key,
            llm_provider=settings.llm_provider,
            use_real_llm=True,
        )
    return _orchestrator


@router.post("/analyze", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None)
):
    """
    Analyze financial query with full verification pipeline.
    
    Flow: Query → Router → LLM/Debate → Truth Boundary → Response
    """
    query_id = str(uuid4())
    
    # Track metrics
    queries_submitted_total.labels(priority="normal").inc()
    
    logger.info(f"Query {query_id}: {request.query[:50]}...")
    
    try:
        # Get orchestrator
        orchestrator = get_orchestrator()
        
        # Process query (async)
        # TODO: Celery for heavy tasks in Phase 1
        result = await orchestrator.process_query_async(
            query_id=query_id,
            query_text=request.query,
            provider=request.provider
        )
        
        return AnalysisResponse(
            query_id=query_id,
            status="completed",
            answer=result.get("answer"),
            verified_fact=result.get("verified_fact"),
            data_source=result.get("data_source", "yfinance"),
            data_freshness=result.get("data_freshness"),
            verification_score=result.get("verification_score", 0.0),
            cost_usd=result.get("cost_usd", 0.0),
            tokens_used=result.get("tokens_used", 0)
        )
        
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
    
    queries_submitted_total.labels(priority="normal").inc()
    
    # TODO: Queue in Celery for Phase 1
    # For now, synchronous
    
    return QueryResponse(
        query_id=query_id,
        status="accepted",
        message="Query accepted for processing",
        estimated_completion=datetime.utcnow() + timedelta(seconds=30)
    )


@router.post("/debate", response_model=AnalysisResponse)
async def debate_query(
    request: QueryRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Run multi-LLM debate on complex query.
    
    Uses Proposer (DeepSeek) + Critic (Claude) + Judge (GPT-4o)
    """
    query_id = str(uuid4())
    
    logger.info(f"Debate {query_id}: {request.query[:50]}...")
    
    # TODO: Full debate pipeline in Phase 1
    # For now, return placeholder
    
    return AnalysisResponse(
        query_id=query_id,
        status="debate_completed",
        answer="Debate result placeholder (Phase 1)",
        verification_score=0.85,
        cost_usd=0.25
    )
