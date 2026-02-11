"""Persistent storage for user price alerts."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor


class PriceAlertStore:
    """Postgres-backed store for price alerts."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = psycopg2.connect(self.db_url)
        self.conn.autocommit = True
        self._init_schema()

    def _init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id VARCHAR(64) PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ticker VARCHAR(10) NOT NULL,
                    condition VARCHAR(10) NOT NULL CHECK (condition IN ('above', 'below')),
                    target_price DOUBLE PRECISION NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    last_checked_at TIMESTAMPTZ NULL,
                    last_triggered_at TIMESTAMPTZ NULL,
                    last_notified_at TIMESTAMPTZ NULL
                )
                """
            )
            # Backward-compatible migration for existing installations.
            cur.execute(
                """
                ALTER TABLE price_alerts
                ADD COLUMN IF NOT EXISTS last_notified_at TIMESTAMPTZ NULL
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_price_alerts_ticker_active
                ON price_alerts(ticker, is_active)
                """
            )

    def create_alert(self, ticker: str, condition: str, target_price: float) -> Dict[str, Any]:
        alert_id = str(uuid.uuid4())
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO price_alerts (
                    id, created_at, ticker, condition, target_price, is_active
                ) VALUES (%s, %s, %s, %s, %s, TRUE)
                RETURNING *
                """,
                (
                    alert_id,
                    datetime.now(UTC),
                    ticker.upper(),
                    condition,
                    float(target_price),
                ),
            )
            return dict(cur.fetchone())

    def list_alerts(self, ticker: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        query = """
            SELECT
                id,
                created_at,
                ticker,
                condition,
                target_price,
                is_active,
                last_checked_at,
                last_triggered_at,
                last_notified_at
            FROM price_alerts
        """
        params: List[Any] = []
        clauses: List[str] = []
        if ticker:
            clauses.append("ticker = %s")
            params.append(ticker.upper())
        if active_only:
            clauses.append("is_active = TRUE")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            return [dict(row) for row in cur.fetchall()]

    def delete_alert(self, alert_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM price_alerts WHERE id = %s", (alert_id,))
            return cur.rowcount > 0

    def mark_checked(self, alert_id: str, triggered: bool):
        with self.conn.cursor() as cur:
            if triggered:
                cur.execute(
                    """
                    UPDATE price_alerts
                    SET last_checked_at = %s, last_triggered_at = %s
                    WHERE id = %s
                    """,
                    (datetime.now(UTC), datetime.now(UTC), alert_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE price_alerts
                    SET last_checked_at = %s
                    WHERE id = %s
                    """,
                    (datetime.now(UTC), alert_id),
                )

    def mark_notified(self, alert_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE price_alerts
                SET last_notified_at = %s
                WHERE id = %s
                """,
                (datetime.now(UTC), alert_id),
            )

    def close(self):
        if self.conn:
            self.conn.close()
