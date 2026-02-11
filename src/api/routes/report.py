"""Report generation routes."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Response, status

from ...graph.neo4j_client import Neo4jClient
from ..config import get_settings


router = APIRouter(prefix="/api", tags=["Reports"])
logger = logging.getLogger(__name__)
settings = get_settings()

_graph_client: Optional[Neo4jClient] = None


def get_graph_client() -> Neo4jClient:
    global _graph_client
    if _graph_client is None:
        _graph_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    return _graph_client


def _build_report_payload(query_id: str, trail: Dict[str, Any]) -> Dict[str, Any]:
    episode = trail.get("episode") or {}
    fact = trail.get("verified_fact") or {}
    synthesis = trail.get("synthesis") or {}
    return {
        "query_id": query_id,
        "query_text": episode.get("query_text"),
        "status": fact.get("status", "unknown"),
        "verification_score": fact.get("confidence_score"),
        "data_source": fact.get("data_source"),
        "code_hash": fact.get("code_hash"),
        "execution_time_ms": fact.get("execution_time_ms"),
        "memory_used_mb": fact.get("memory_used_mb"),
        "confidence_before": synthesis.get("original_confidence"),
        "confidence_after": synthesis.get("adjusted_confidence"),
        "key_risks": synthesis.get("key_risks", []),
        "key_opportunities": synthesis.get("key_opportunities", []),
        "synthesis": synthesis,
        "provenance": {
            "episode_id": episode.get("episode_id"),
            "fact_id": fact.get("fact_id"),
            "synthesis_id": synthesis.get("synthesis_id"),
            "production_path": "langgraph",
            "bypasses": [],
        },
        "disclaimer": "This analysis is for informational purposes only...",
    }


def _render_markdown(payload: Dict[str, Any]) -> str:
    risks = payload.get("key_risks") or []
    opps = payload.get("key_opportunities") or []
    return (
        f"# Analysis Report\n\n"
        f"- Query ID: `{payload.get('query_id')}`\n"
        f"- Query: {payload.get('query_text')}\n"
        f"- Status: {payload.get('status')}\n"
        f"- Verification Score: {payload.get('verification_score')}\n"
        f"- Data Source: {payload.get('data_source')}\n\n"
        f"## Execution\n\n"
        f"- Code Hash: `{payload.get('code_hash')}`\n"
        f"- Execution Time: {payload.get('execution_time_ms')} ms\n"
        f"- Memory: {payload.get('memory_used_mb')} MB\n\n"
        f"## Debate Impact\n\n"
        f"- Confidence Before: {payload.get('confidence_before')}\n"
        f"- Confidence After: {payload.get('confidence_after')}\n\n"
        f"## Key Risks\n\n"
        + "".join(f"- {item}\n" for item in risks)
        + "\n## Key Opportunities\n\n"
        + "".join(f"- {item}\n" for item in opps)
        + "\n## Disclaimer\n\n"
        + payload.get("disclaimer", "")
    )


@router.get("/report/{query_id}")
async def get_query_report(
    query_id: str,
    format: str = Query("json", pattern="^(json|md)$"),
):
    """Generate downloadable report for query id."""
    try:
        graph = get_graph_client()
        trail = graph.get_audit_trail(query_id)
        if not trail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report source for query {query_id} not found",
            )

        payload = _build_report_payload(query_id, trail)

        if format == "json":
            return Response(
                content=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=report_{query_id}.json"},
            )

        markdown = _render_markdown(payload)
        return Response(
            content=markdown,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=report_{query_id}.md"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate report for {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )

