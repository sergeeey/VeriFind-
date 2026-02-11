"""Audit and verification transparency API routes."""

from typing import Any, Dict, Optional, List
import logging
import re
import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query, Response, status
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


class VerificationTransparencyResponse(BaseModel):
    """Response model for verification score transparency endpoint."""

    query_id: str
    query_text: str
    verification_score: Optional[float] = None
    confidence_before: Optional[float] = None
    confidence_after: Optional[float] = None
    confidence_delta: Optional[float] = None
    confidence_rationale: Optional[str] = None
    debate_quality_score: Optional[float] = None
    areas_of_agreement: List[str] = Field(default_factory=list)
    areas_of_disagreement: List[str] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    key_opportunities: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)


def _extract_synthesis_payload(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """Extract normalized synthesis payload from node + optional raw_payload."""
    raw_payload = synthesis.get("raw_payload")
    merged: Dict[str, Any] = {}
    if isinstance(raw_payload, dict):
        merged.update(raw_payload)
    merged.update(synthesis)
    return merged


def _as_list(value: Any) -> List[str]:
    """Normalize optional list-like fields to list[str]."""
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _build_audit_payload(query_id: str, trail_data: Dict[str, Any]) -> AuditTrailResponse:
    """Build normalized audit response payload from graph trail data."""
    fact = trail_data.get("verified_fact") or {}
    synthesis = trail_data.get("synthesis") or {}
    query_text = (trail_data.get("episode") or {}).get("query_text", "")

    return AuditTrailResponse(
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

        return _build_audit_payload(query_id=query_id, trail_data=trail_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit trail for {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit trail",
        )


@router.get("/audit/{query_id}/export")
async def export_audit_trail(
    query_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
):
    """Export audit trail with provenance chain as JSON or CSV."""
    try:
        graph = get_graph_client()
        trail_data = graph.get_audit_trail(query_id)

        if not trail_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit trail for query {query_id} not found",
            )

        payload = _build_audit_payload(query_id=query_id, trail_data=trail_data)
        payload_dict = payload.model_dump()

        if format == "json":
            return Response(
                content=json.dumps(payload_dict, ensure_ascii=False, default=str, indent=2),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=audit_{query_id}.json"
                },
            )

        trail = payload_dict.get("trail", {})
        verified_fact = trail.get("verified_fact", {})
        debate = trail.get("debate", {})
        synthesis = trail.get("synthesis", {})
        csv_row = {
            "query_id": payload_dict.get("query_id"),
            "query_text": payload_dict.get("query_text"),
            "fact_id": verified_fact.get("fact_id"),
            "verification_score": verified_fact.get("confidence_score"),
            "data_source": verified_fact.get("data_source"),
            "code_hash": trail.get("execution", {}).get("code_hash"),
            "execution_status": trail.get("execution", {}).get("status"),
            "confidence_before": debate.get("confidence_before"),
            "confidence_after": debate.get("confidence_after"),
            "key_risks": ",".join(debate.get("key_risks") or []),
            "key_opportunities": ",".join(debate.get("key_opportunities") or []),
            "synthesis_id": synthesis.get("synthesis_id"),
        }

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(csv_row.keys()))
        writer.writeheader()
        writer.writerow(csv_row)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_{query_id}.csv"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export audit trail for {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit trail",
        )


@router.get("/verification/{query_id}", response_model=VerificationTransparencyResponse)
async def get_verification_transparency(query_id: str):
    """Get normalized explanation for how verification score was produced."""
    try:
        graph = get_graph_client()
        trail_data = graph.get_audit_trail(query_id)

        if not trail_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification trail for query {query_id} not found",
            )

        fact = trail_data.get("verified_fact") or {}
        synthesis = trail_data.get("synthesis") or {}
        synthesis_payload = _extract_synthesis_payload(synthesis)
        query_text = (trail_data.get("episode") or {}).get("query_text", "")

        confidence_before = synthesis_payload.get("original_confidence")
        confidence_after = synthesis_payload.get("adjusted_confidence")

        verification_score = (
            confidence_after
            if confidence_after is not None
            else fact.get("confidence_score")
        )

        confidence_delta = None
        if confidence_before is not None and confidence_after is not None:
            confidence_delta = round(confidence_after - confidence_before, 6)

        return VerificationTransparencyResponse(
            query_id=query_id,
            query_text=query_text,
            verification_score=verification_score,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            confidence_delta=confidence_delta,
            confidence_rationale=synthesis_payload.get("confidence_rationale"),
            debate_quality_score=synthesis_payload.get("debate_quality_score"),
            areas_of_agreement=_as_list(synthesis_payload.get("areas_of_agreement")),
            areas_of_disagreement=_as_list(synthesis_payload.get("areas_of_disagreement")),
            key_risks=_as_list(synthesis_payload.get("key_risks")),
            key_opportunities=_as_list(synthesis_payload.get("key_opportunities")),
            provenance={
                "fact_id": fact.get("fact_id"),
                "synthesis_id": synthesis.get("synthesis_id"),
                "code_hash": fact.get("code_hash"),
                "data_source": fact.get("data_source"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get verification transparency for {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve verification transparency",
        )
