"""Query history storage for API sessions."""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
import logging
import re

import psycopg2
from psycopg2.extras import RealDictCursor


logger = logging.getLogger(__name__)


class QueryHistoryStore:
    """Timescale/Postgres-backed query history store."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = psycopg2.connect(self.db_url)
        self.conn.autocommit = True
        self._init_schema()

    def _init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS query_history (
                    id VARCHAR(64) PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    query_text TEXT NOT NULL,
                    status VARCHAR(20),
                    result_summary TEXT,
                    confidence_score FLOAT,
                    ticker_mentions TEXT[] DEFAULT '{}'
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_query_history_created_at
                ON query_history(created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_query_history_tickers
                ON query_history USING GIN (ticker_mentions)
                """
            )

    @staticmethod
    def extract_ticker_mentions(query_text: str) -> List[str]:
        """Extract probable stock ticker mentions from query text."""
        candidates = re.findall(r"\b[A-Z]{1,5}\b", query_text.upper())
        stopwords = {"WHAT", "WHEN", "WHERE", "ABOUT", "PRICE", "RATIO", "AND", "OR"}
        deduped = []
        for token in candidates:
            if token not in stopwords and token not in deduped:
                deduped.append(token)
        return deduped

    def save_entry(
        self,
        query_id: str,
        query_text: str,
        status: str,
        result_summary: Optional[str] = None,
        confidence_score: Optional[float] = None,
        ticker_mentions: Optional[List[str]] = None,
    ):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_history (
                    id, created_at, query_text, status, result_summary, confidence_score, ticker_mentions
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    result_summary = EXCLUDED.result_summary,
                    confidence_score = EXCLUDED.confidence_score,
                    ticker_mentions = EXCLUDED.ticker_mentions
                """,
                (
                    query_id,
                    datetime.now(UTC),
                    query_text,
                    status,
                    result_summary,
                    confidence_score,
                    ticker_mentions or [],
                ),
            )

    def get_history(self, limit: int = 20, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT id, created_at, query_text, status, result_summary, confidence_score, ticker_mentions
            FROM query_history
        """
        params: List[Any] = []
        if ticker:
            query += " WHERE %s = ANY(ticker_mentions)"
            params.append(ticker.upper())
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def search_history(self, search_query: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, created_at, query_text, status, result_summary, confidence_score, ticker_mentions
                FROM query_history
                WHERE query_text ILIKE %s OR COALESCE(result_summary, '') ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (f"%{search_query}%", f"%{search_query}%", limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_entry(self, query_id: str) -> Optional[Dict[str, Any]]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, created_at, query_text, status, result_summary, confidence_score, ticker_mentions
                FROM query_history
                WHERE id = %s
                """,
                (query_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_entry(self, query_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM query_history WHERE id = %s", (query_id,))
            return cur.rowcount > 0

    def close(self):
        if self.conn:
            self.conn.close()
