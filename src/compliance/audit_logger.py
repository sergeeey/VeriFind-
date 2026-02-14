"""
Immutable audit logger for financial compliance.

Week 13 Day 1: Logs all analysis requests and responses to TimescaleDB.

Regulatory Requirements:
- SEC: Investment Advisers Act - record retention
- MiFID II (EU): 5+ year record retention for trade-related communications
- EU AI Act: High-risk AI systems must maintain audit trail

Privacy Protection:
- NO PII in logs (client IPs are hashed, requests are hashed)
- Only response summaries stored (recommendation, confidence, cost)
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import asyncpg

logger = logging.getLogger(__name__)


class AuditLogger:
    """Logs financial analysis events for regulatory compliance."""

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize audit logger.

        Args:
            db_pool: AsyncPG connection pool to TimescaleDB
        """
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)

    async def log_analysis(
        self,
        query_id: str,
        endpoint: str,
        recommendation: Optional[str],
        confidence: Optional[float],
        cost_usd: float,
        llm_providers: Dict[str, str],
        processing_time_ms: float,
        client_ip: str = "unknown",
        request_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an analysis event to the immutable audit trail.

        Args:
            query_id: Unique query identifier
            endpoint: API endpoint (e.g., "/api/analyze-debate")
            recommendation: Final recommendation (BUY/HOLD/SELL)
            confidence: Confidence score (0.0-1.0)
            cost_usd: Total cost of analysis
            llm_providers: Dict of LLM providers used (e.g., {"bull": "deepseek"})
            processing_time_ms: Processing time in milliseconds
            client_ip: Client IP address (will be hashed)
            request_data: Optional request data for hashing (NOT stored)

        Returns:
            None (log-only operation)
        """
        try:
            # Hash client IP for privacy (16-char truncated SHA-256)
            client_ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]

            # Hash request data if provided (for deduplication)
            request_hash = None
            if request_data:
                request_str = json.dumps(request_data, sort_keys=True)
                request_hash = hashlib.sha256(request_str.encode()).hexdigest()

            # Response summary (NO PII)
            response_summary = {
                "recommendation": recommendation,
                "confidence": confidence,
                "cost_usd": cost_usd,
            }

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_log
                    (event_type, query_id, endpoint, request_hash, response_summary,
                     llm_providers, processing_time_ms, client_ip_hash)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    "analysis_request",
                    query_id,
                    endpoint,
                    request_hash,
                    json.dumps(response_summary),
                    json.dumps(llm_providers),
                    processing_time_ms,
                    client_ip_hash,
                )

            self.logger.info(
                f"Audit log: analysis_request | Query: {query_id[:8]} | "
                f"Endpoint: {endpoint} | Cost: ${cost_usd:.4f}",
                extra={
                    "query_id": query_id,
                    "endpoint": endpoint,
                    "cost_usd": cost_usd,
                    "processing_time_ms": processing_time_ms,
                },
            )

        except Exception as e:
            # NEVER fail the request due to audit logging error
            self.logger.error(f"Audit logging failed: {e}", exc_info=True)

    async def get_audit_trail(
        self,
        query_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """
        Retrieve audit trail for compliance queries.

        Args:
            query_id: Optional filter by query ID
            endpoint: Optional filter by endpoint
            start_date: Optional filter by start date
            end_date: Optional filter by end date
            limit: Max number of results (default 100)

        Returns:
            List of audit log entries
        """
        try:
            conditions = []
            params = []
            param_idx = 1

            if query_id:
                conditions.append(f"query_id = ${param_idx}")
                params.append(query_id)
                param_idx += 1

            if endpoint:
                conditions.append(f"endpoint = ${param_idx}")
                params.append(endpoint)
                param_idx += 1

            if start_date:
                conditions.append(f"timestamp >= ${param_idx}")
                params.append(start_date)
                param_idx += 1

            if end_date:
                conditions.append(f"timestamp <= ${param_idx}")
                params.append(end_date)
                param_idx += 1

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            query = f"""
                SELECT id, timestamp, event_type, query_id, endpoint,
                       response_summary, llm_providers, disclaimer_version,
                       processing_time_ms
                FROM audit_log
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_idx}
            """
            params.append(limit)

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Audit trail query failed: {e}", exc_info=True)
            return []
