"""Audit trail API routes."""

from typing import Any, Dict, Optional
import logging
import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...graph.neo4j_client import Neo4jClient
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["Audit"])
logger = logging.getLogger(__name__)
settings = get_settings()

_graph_client: Optional[Neo4jClient] = None


def get_graph_client() -> Neo4jClient:
    """Get Neo4j client instance."""
    global _graph_client
    if _graph_client is None:
        _graph_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    return _graph_client


def _redact_secrets(value: Optional[str]) -> Optional[str]:
    """Best-effort redaction for accidental secrets in captured source code."""
    if not value:
        return value

    redacted = re.sub(r"sk-[A-Za-z0-9_\-]{10,}", "[REDACTED_API_KEY]", value)
    redacted = re.sub(
        r"(?i)(api[_-]?key|token|password)\s*=\s*['\"][^'\"]+['\"]",
        r"\1='[REDACTED]'",
        redacted,
    )
    return redacted


class AuditTrailResponse(BaseModel):
    """Response model for audit trail endpoint."""

    query_id: str
    query_text: str
    trail: Dict[str, Any] = Field(default_factory=dict)


@router.get("/audit/{query_id}", response_model=AuditTrailResponse)
async def get_audit_trail(query_id: str):
    """Get audit trail for a query from graph artifacts."""
    try:
        graph = get_graph_client()
        trail_data = graph.get_audit_trail(query_id)

        if not trail_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit trail for query {query_id} not found",
            )

        fact = trail_data.get("verified_fact") or {}
        synthesis = trail_data.get("synthesis") or {}

        query_text = (trail_data.get("episode") or {}).get("query_text", "")

        response = AuditTrailResponse(
            query_id=query_id,
            query_text=query_text,
            trail={
                "plan": {
                    "code": _redact_secrets(fact.get("source_code")),
                    "provider": "unknown",
                    "code_hash": fact.get("code_hash"),
                },
                "execution": {
                    "duration_ms": fact.get("execution_time_ms"),
                    "memory_mb": fact.get("memory_used_mb"),
                    "status": fact.get("status"),
                    "code_hash": fact.get("code_hash"),
                },
                "verified_fact": fact,
                "debate": {
                    "available": bool(synthesis),
                    "key_risks": synthesis.get("key_risks", []),
                    "key_opportunities": synthesis.get("key_opportunities", []),
                    "confidence_before": synthesis.get("original_confidence"),
                    "confidence_after": synthesis.get("adjusted_confidence"),
                },
                "synthesis": synthesis,
            },
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit trail for {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit trail",
        )
