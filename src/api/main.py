"""
FastAPI REST API for APE 2026
Week 6 Day 4 - Production API Layer

Endpoints:
- POST /query - Execute financial analysis query
- GET /status/{query_id} - Get query execution status
- GET /episodes/{episode_id} - Get episode details
- GET /facts - List verified facts
- GET /health - Health check
"""

from fastapi import FastAPI, HTTPException, Depends, status, Header, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
import logging
from uuid import uuid4
import asyncio
import json

from pydantic import BaseModel, Field, validator

from ..orchestration.langgraph_orchestrator import LangGraphOrchestrator, APEState
from ..storage.timescale_store import TimescaleDBStore
from ..graph.neo4j_client import Neo4jClient
from .security import input_validator, rate_limiter
from .config import get_settings, load_production_api_keys

# Load settings
settings = get_settings()

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    """
    Add security headers to all responses.

    Headers:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter
    - Strict-Transport-Security: Enforce HTTPS (production)
    - Content-Security-Policy: Restrict resource loading
    """
    response = await call_next(request)

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Enable XSS protection (legacy, but still useful)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # TODO: Enable HSTS in production (requires HTTPS)
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Content Security Policy (restrictive)
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",  # Allow inline scripts for API docs
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self' ws: wss:",  # Allow WebSocket connections
        "frame-ancestors 'none'",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions policy (restrict features)
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    return response

# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for query execution."""
    query: str = Field(..., min_length=10, max_length=1000, description="Financial analysis query")
    priority: Optional[str] = Field("normal", description="Query priority: low, normal, high")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @validator('query')
    def validate_query(cls, v):
        """
        Validate query content with security checks.

        Checks for:
        - SQL injection patterns
        - XSS patterns
        - Command injection patterns
        """
        if not v.strip():
            raise ValueError("Query cannot be empty")

        # Security validation
        validation = input_validator.validate_query(v)
        if not validation.is_valid:
            raise ValueError(f"Security validation failed: {validation.error_message}")

        # Return sanitized value
        return validation.sanitized_value

    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority level."""
        if v not in ['low', 'normal', 'high']:
            raise ValueError("Priority must be: low, normal, or high")
        return v


class QueryResponse(BaseModel):
    """Response model for query submission."""
    query_id: str = Field(..., description="Unique query identifier")
    status: str = Field(..., description="Query status")
    message: str = Field(..., description="Human-readable message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


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


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: datetime
    version: str
    components: Dict[str, str]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    timestamp: str  # ISO format datetime string

    @classmethod
    def create(cls, error: str, detail: Optional[str] = None) -> "ErrorResponse":
        """Create error response with current timestamp."""
        return cls(
            error=error,
            detail=detail,
            timestamp=datetime.utcnow().isoformat()
        )


# ============================================================================
# Authentication & Rate Limiting
# ============================================================================

# Load API keys from settings and environment
API_KEYS = {**settings.api_keys, **load_production_api_keys()}


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header."
        )

    if x_api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return x_api_key


async def check_rate_limit(api_key: str = Depends(verify_api_key)) -> str:
    """
    Check rate limit for API key using advanced rate limiter.

    Uses per-endpoint limits with burst protection and exponential backoff.
    """
    # Get rate limit for this API key
    limit = API_KEYS[api_key].get("rate_limit", settings.default_rate_limit)

    # Check rate limit with burst protection
    is_allowed, error_message = rate_limiter.check_rate_limit(
        key=api_key,
        endpoint="query",  # Can be customized per endpoint
        limit=limit,
        window_seconds=settings.rate_limit_window_hours * 3600,
        burst_limit=settings.default_rate_limit // 10  # 10% of hourly limit per minute
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_message
        )

    return api_key


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Supports subscribing to specific query_id updates.
    """

    def __init__(self):
        # Map of query_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> set of query_ids (for cleanup)
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.subscriptions[websocket] = set()
        logger.info(f"WebSocket connected: {id(websocket)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and cleanup subscriptions."""
        async with self._lock:
            # Remove from all query subscriptions
            if websocket in self.subscriptions:
                for query_id in self.subscriptions[websocket]:
                    if query_id in self.active_connections:
                        self.active_connections[query_id].discard(websocket)
                        # Cleanup empty subscription sets
                        if not self.active_connections[query_id]:
                            del self.active_connections[query_id]

                del self.subscriptions[websocket]

        logger.info(f"WebSocket disconnected: {id(websocket)}")

    async def subscribe(self, websocket: WebSocket, query_id: str):
        """Subscribe WebSocket to query_id updates."""
        async with self._lock:
            if query_id not in self.active_connections:
                self.active_connections[query_id] = set()

            self.active_connections[query_id].add(websocket)

            if websocket not in self.subscriptions:
                self.subscriptions[websocket] = set()
            self.subscriptions[websocket].add(query_id)

        logger.info(f"WebSocket {id(websocket)} subscribed to query {query_id}")

    async def unsubscribe(self, websocket: WebSocket, query_id: str):
        """Unsubscribe WebSocket from query_id updates."""
        async with self._lock:
            if query_id in self.active_connections:
                self.active_connections[query_id].discard(websocket)
                if not self.active_connections[query_id]:
                    del self.active_connections[query_id]

            if websocket in self.subscriptions:
                self.subscriptions[websocket].discard(query_id)

        logger.info(f"WebSocket {id(websocket)} unsubscribed from query {query_id}")

    async def broadcast_to_query(self, query_id: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a specific query."""
        async with self._lock:
            connections = self.active_connections.get(query_id, set()).copy()

        if not connections:
            logger.debug(f"No active connections for query {query_id}")
            return

        message_json = json.dumps(message)
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket {id(websocket)}: {e}")
                disconnected.append(websocket)

        # Cleanup disconnected WebSockets
        for websocket in disconnected:
            await self.disconnect(websocket)

        logger.info(f"Broadcasted to {len(connections) - len(disconnected)} connections for query {query_id}")

    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)


# Global ConnectionManager instance
connection_manager = ConnectionManager()


# ============================================================================
# WebSocket Helper Functions
# ============================================================================

async def broadcast_query_update(
    query_id: str,
    status: str,
    current_node: Optional[str] = None,
    progress: float = 0.0,
    verified_facts_count: int = 0,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Broadcast query status update to all subscribed WebSocket clients.

    This function can be called from anywhere in the application to push
    real-time updates to connected clients.

    Args:
        query_id: Query identifier
        status: Current status (e.g., "processing", "completed", "failed")
        current_node: Current pipeline node (e.g., "PLAN", "VEE", "GATE")
        progress: Completion progress (0.0 to 1.0)
        verified_facts_count: Number of facts generated so far
        error: Error message if status is "failed"
        metadata: Additional metadata to include
    """
    message = {
        "query_id": query_id,
        "data": {
            "status": status,
            "current_node": current_node,
            "progress": progress,
            "verified_facts_count": verified_facts_count,
            "error": error,
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
    }

    await connection_manager.broadcast_to_query(query_id, message)


# ============================================================================
# Background Tasks
# ============================================================================

def run_query_orchestrator(query_id: str, query_text: str, direct_code: Optional[str] = None):
    """
    Background task to run orchestrator.

    This function runs in a background thread and executes the full APE pipeline.

    Args:
        query_id: Query identifier
        query_text: User query
        direct_code: Optional direct code for testing
    """
    try:
        logger.info(f"Starting orchestrator for query {query_id}")

        orchestrator = get_orchestrator()

        # Run orchestrator (this will broadcast updates via WebSocket)
        final_state = orchestrator.run(
            query_id=query_id,
            query_text=query_text,
            direct_code=direct_code
        )

        if final_state.status.value == 'completed':
            logger.info(f"Query {query_id} completed successfully")
        else:
            logger.error(f"Query {query_id} failed: {final_state.error_message}")

    except Exception as e:
        logger.error(f"Orchestrator failed for query {query_id}: {e}", exc_info=True)

        # Broadcast failure
        try:
            asyncio.run(
                broadcast_query_update(
                    query_id=query_id,
                    status="failed",
                    current_node=None,
                    progress=0.0,
                    verified_facts_count=0,
                    error=f"Orchestrator exception: {str(e)}"
                )
            )
        except:
            pass  # Best effort


# ============================================================================
# Dependency Injection
# ============================================================================

def get_orchestrator() -> LangGraphOrchestrator:
    """Get orchestrator instance with WebSocket broadcast callback."""
    # TODO: Implement proper dependency injection with singleton
    return LangGraphOrchestrator(
        claude_api_key=None,  # Not needed for testing with direct_code
        broadcast_callback=broadcast_query_update
    )


def get_timescale_store() -> TimescaleDBStore:
    """Get TimescaleDB store instance."""
    # TODO: Implement proper dependency injection
    return TimescaleDBStore()


def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client instance."""
    # TODO: Implement proper dependency injection
    return Neo4jClient()


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return JSONResponse({
        "message": "APE 2026 API",
        "docs": "/docs",
        "health": "/health"
    })


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns system status and component health.
    """
    try:
        # TODO: Check actual component health
        components = {
            "api": "healthy",
            "orchestrator": "healthy",
            "timescaledb": "unknown",  # TODO: ping database
            "neo4j": "unknown",  # TODO: ping database
            "chromadb": "healthy"
        }

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            components=components
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.post("/query", response_model=QueryResponse, tags=["Query"], status_code=status.HTTP_202_ACCEPTED)
async def submit_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(check_rate_limit)
):
    """
    Submit a financial analysis query for execution.

    The query will be processed asynchronously through the APE pipeline:
    PLAN → FETCH → VEE → GATE → DEBATE

    Real-time updates will be broadcast via WebSocket to subscribed clients.

    Returns a query ID for status tracking.
    """
    try:
        query_id = str(uuid4())

        logger.info(f"Query submitted: {query_id} | API Key: {API_KEYS[api_key]['name']}")
        logger.info(f"Query text: {request.query}")

        # Broadcast initial status to WebSocket subscribers
        await broadcast_query_update(
            query_id=query_id,
            status="accepted",
            current_node=None,
            progress=0.0,
            verified_facts_count=0,
            metadata={"priority": request.priority, "query_text": request.query}
        )

        # Example code for testing (calculates 2+2)
        # In production, this would come from PLAN node (Claude API)
        test_code = """
import json
result = 2 + 2
output = {"calculation": "2+2", "result": result}
print(json.dumps(output))
"""

        # Run orchestrator in background
        # This will automatically broadcast updates at each node via WebSocket
        background_tasks.add_task(
            run_query_orchestrator,
            query_id=query_id,
            query_text=request.query,
            direct_code=test_code  # Remove this in production
        )

        # Estimate completion time (simple heuristic)
        estimated_seconds = 10 if request.priority == "high" else 30
        estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)

        return QueryResponse(
            query_id=query_id,
            status="accepted",
            message="Query accepted for processing. Subscribe to WebSocket for real-time updates.",
            estimated_completion=estimated_completion
        )

    except Exception as e:
        logger.error(f"Query submission failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit query: {str(e)}"
        )


@app.get("/status/{query_id}", response_model=StatusResponse, tags=["Query"])
async def get_query_status(
    query_id: str,
    api_key: str = Depends(verify_api_key),
    store: TimescaleDBStore = Depends(get_timescale_store)
):
    """
    Get execution status of a query.

    Returns current status, progress, and any verified facts generated.
    """
    try:
        # TODO: Implement actual status retrieval from storage
        # For now, return mock status

        logger.info(f"Status requested for query: {query_id}")

        # Mock response
        return StatusResponse(
            query_id=query_id,
            status="processing",
            current_node="VEE",
            progress=0.6,
            verified_facts_count=2,
            created_at=datetime.utcnow() - timedelta(minutes=2),
            updated_at=datetime.utcnow(),
            metadata={"priority": "normal"}
        )

    except Exception as e:
        logger.error(f"Status retrieval failed for {query_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query not found: {query_id}"
        )


@app.get("/episodes/{episode_id}", response_model=EpisodeResponse, tags=["Episodes"])
async def get_episode(
    episode_id: str,
    api_key: str = Depends(verify_api_key),
    neo4j: Neo4jClient = Depends(get_neo4j_client)
):
    """
    Get episode details including all verified facts and synthesis.

    An episode represents a complete query execution with all generated facts.
    """
    try:
        logger.info(f"Episode requested: {episode_id}")

        # TODO: Implement actual episode retrieval from Neo4j

        # Mock response
        return EpisodeResponse(
            episode_id=episode_id,
            query_id=str(uuid4()),
            query_text="Calculate Sharpe ratio of SPY for 2023",
            status="completed",
            verified_facts=[
                VerifiedFactResponse(
                    fact_id=str(uuid4()),
                    query_id=str(uuid4()),
                    statement="SPY Sharpe ratio for 2023 is 1.45",
                    value=1.45,
                    confidence_score=0.92,
                    source_code="sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252))",
                    created_at=datetime.utcnow(),
                    metadata={"source": "VEE"}
                )
            ],
            synthesis={"verdict": "ACCEPT", "confidence": 0.89},
            created_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow(),
            execution_time_ms=4523.5
        )

    except Exception as e:
        logger.error(f"Episode retrieval failed for {episode_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode not found: {episode_id}"
        )


@app.get("/facts", response_model=List[VerifiedFactResponse], tags=["Facts"])
async def list_facts(
    query_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key),
    store: TimescaleDBStore = Depends(get_timescale_store)
):
    """
    List verified facts.

    Optionally filter by query_id. Supports pagination.
    """
    try:
        logger.info(f"Facts list requested: query_id={query_id}, limit={limit}, offset={offset}")

        # TODO: Implement actual fact retrieval from TimescaleDB

        # Mock response
        return [
            VerifiedFactResponse(
                fact_id=str(uuid4()),
                query_id=query_id or str(uuid4()),
                statement="Mock verified fact",
                value=123.45,
                confidence_score=0.87,
                created_at=datetime.utcnow(),
                metadata={}
            )
        ]

    except Exception as e:
        logger.error(f"Facts retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve facts"
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, api_key: Optional[str] = Query(None)):
    """
    WebSocket endpoint for real-time query status updates.

    Authentication:
    - Pass API key as query parameter: ws://localhost:8000/ws?api_key=your_key
    - Or send {"action": "auth", "api_key": "..."} as first message

    Protocol:
    1. Client connects (with api_key in query params OR sends auth message)
    2. Client sends: {"action": "subscribe", "query_id": "..."}
    3. Server broadcasts updates: {"query_id": "...", "data": {...}}
    4. Client sends: {"action": "unsubscribe", "query_id": "..."}
    5. Client disconnects

    Example message from server:
    {
        "query_id": "abc-123",
        "data": {
            "status": "processing",
            "current_node": "VEE",
            "progress": 0.6,
            "verified_facts_count": 2,
            "updated_at": "2026-02-08T12:00:00Z"
        }
    }
    """
    # Accept connection first (required before sending messages)
    await connection_manager.connect(websocket)

    # Authentication check
    authenticated = False
    if api_key and api_key in API_KEYS:
        authenticated = True
        await connection_manager.send_personal_message(
            websocket,
            {
                "status": "authenticated",
                "message": f"Authenticated as {API_KEYS[api_key]['name']}"
            }
        )
    else:
        # Wait for auth message
        await connection_manager.send_personal_message(
            websocket,
            {
                "status": "auth_required",
                "message": "Please authenticate with {action: 'auth', api_key: '...'} or connect with ?api_key=..."
            }
        )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                # Handle authentication action
                if action == "auth":
                    auth_key = message.get("api_key")
                    if auth_key and auth_key in API_KEYS:
                        authenticated = True
                        await connection_manager.send_personal_message(
                            websocket,
                            {
                                "status": "authenticated",
                                "message": f"Authenticated as {API_KEYS[auth_key]['name']}"
                            }
                        )
                    else:
                        await connection_manager.send_personal_message(
                            websocket,
                            {"error": "Invalid API key"}
                        )
                    continue

                # Check authentication for all other actions
                if not authenticated:
                    await connection_manager.send_personal_message(
                        websocket,
                        {
                            "error": "Not authenticated. Please authenticate first.",
                            "hint": "Send {action: 'auth', api_key: '...'}"
                        }
                    )
                    continue

                # Validate query_id if present
                query_id = message.get("query_id")
                if query_id:
                    validation = input_validator.validate_query_id(query_id)
                    if not validation.is_valid:
                        await connection_manager.send_personal_message(
                            websocket,
                            {"error": validation.error_message}
                        )
                        continue

                if not action:
                    await connection_manager.send_personal_message(
                        websocket,
                        {"error": "Missing 'action' field"}
                    )
                    continue

                if action == "subscribe":
                    if not query_id:
                        await connection_manager.send_personal_message(
                            websocket,
                            {"error": "Missing 'query_id' for subscribe action"}
                        )
                        continue
                    await connection_manager.subscribe(websocket, query_id)
                    await connection_manager.send_personal_message(
                        websocket,
                        {
                            "status": "subscribed",
                            "query_id": query_id,
                            "message": f"Subscribed to updates for query {query_id}"
                        }
                    )

                elif action == "unsubscribe":
                    await connection_manager.unsubscribe(websocket, query_id)
                    await connection_manager.send_personal_message(
                        websocket,
                        {
                            "status": "unsubscribed",
                            "query_id": query_id,
                            "message": f"Unsubscribed from query {query_id}"
                        }
                    )

                elif action == "ping":
                    # Heartbeat support
                    await connection_manager.send_personal_message(
                        websocket,
                        {"status": "pong", "timestamp": datetime.utcnow().isoformat()}
                    )

                else:
                    await connection_manager.send_personal_message(
                        websocket,
                        {
                            "error": f"Unknown action: {action}",
                            "supported_actions": ["subscribe", "unsubscribe", "ping"]
                        }
                    )

            except json.JSONDecodeError:
                await connection_manager.send_personal_message(
                    websocket,
                    {"error": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                await connection_manager.send_personal_message(
                    websocket,
                    {"error": f"Server error: {str(e)}"}
                )

    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await connection_manager.disconnect(websocket)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with standard error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.create(error=exc.detail).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse.create(
            error="Internal server error",
            detail=str(exc)
        ).dict()
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("🚀 APE 2026 API starting...")
    logger.info("📊 Initializing components...")
    # TODO: Initialize database connections, load models, etc.
    logger.info("✅ API ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 APE 2026 API shutting down...")
    # TODO: Close database connections, cleanup resources
    logger.info("✅ Shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
