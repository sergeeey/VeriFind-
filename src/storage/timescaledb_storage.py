"""
TimescaleDB Storage for VerifiedFacts.

Week 3 Day 2: Persistent storage with time-series optimization.

Features:
- Hypertable on created_at for efficient time-range queries
- JSON storage for extracted_values
- Indexes on query_id, plan_id, status
- Aggregation queries for metrics
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from src.truth_boundary.gate import VerifiedFact


class TimescaleDBStorage:
    """
    TimescaleDB storage for VerifiedFacts.

    Schema:
    - verified_facts table with hypertable on created_at
    - Efficient time-range queries
    - JSON column for extracted_values
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5433,
        database: str = 'ape_timeseries',
        user: str = 'ape',
        password: str = 'ape_timescale_password'
    ):
        """
        Initialize TimescaleDB connection.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user

        self.logger = logging.getLogger(__name__)

        try:
            self.conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            self.conn.autocommit = True
            self.logger.info(f"Connected to TimescaleDB at {host}:{port}/{database}")
        except Exception as e:
            self.logger.error(f"Failed to connect to TimescaleDB: {e}")
            raise

    def is_connected(self) -> bool:
        """Check if database connection is active."""
        try:
            with self.conn.cursor() as cur:
                cur.execute('SELECT 1')
            return True
        except:
            return False

    def init_schema(self):
        """
        Initialize database schema.

        Creates verified_facts table and converts to hypertable.
        """
        with self.conn.cursor() as cur:
            # Create table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verified_facts (
                    fact_id VARCHAR(255) NOT NULL,
                    query_id VARCHAR(255) NOT NULL,
                    plan_id VARCHAR(255) NOT NULL,
                    code_hash VARCHAR(255),
                    status VARCHAR(50) NOT NULL,
                    extracted_values JSONB NOT NULL,
                    execution_time_ms INTEGER,
                    memory_used_mb FLOAT,
                    created_at TIMESTAMPTZ NOT NULL,
                    error_message TEXT,
                    PRIMARY KEY (fact_id, created_at)
                )
            """)

            # Create hypertable if not already
            # Check if already a hypertable
            cur.execute("""
                SELECT * FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'verified_facts'
            """)

            if cur.fetchone() is None:
                cur.execute("""
                    SELECT create_hypertable(
                        'verified_facts',
                        'created_at',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    )
                """)
                self.logger.info("Created hypertable on verified_facts")

            # Create indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_verified_facts_query_id
                ON verified_facts(query_id, created_at DESC)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_verified_facts_status
                ON verified_facts(status, created_at DESC)
            """)

            self.logger.info("Schema initialized")

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (table_name,))
            return cur.fetchone()[0]

    def is_hypertable(self, table_name: str) -> bool:
        """Check if table is a hypertable."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM timescaledb_information.hypertables
                    WHERE hypertable_name = %s
                )
            """, (table_name,))
            return cur.fetchone()[0]

    def store_fact(self, fact: VerifiedFact):
        """
        Store a VerifiedFact in database.

        Args:
            fact: VerifiedFact object to store
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO verified_facts (
                    fact_id, query_id, plan_id, code_hash, status,
                    extracted_values, execution_time_ms, memory_used_mb,
                    created_at, error_message
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (fact_id, created_at) DO NOTHING
            """, (
                fact.fact_id,
                fact.query_id,
                fact.plan_id,
                fact.code_hash,
                fact.status,
                Json(fact.extracted_values),
                fact.execution_time_ms,
                fact.memory_used_mb,
                fact.created_at,
                fact.error_message
            ))

        self.logger.info(f"Stored fact {fact.fact_id}")

    def get_fact_by_id(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve fact by ID.

        Args:
            fact_id: Fact identifier

        Returns:
            Dictionary with fact data or None
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM verified_facts
                WHERE fact_id = %s
            """, (fact_id,))

            row = cur.fetchone()
            return dict(row) if row else None

    def get_facts_by_query(self, query_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all facts for a query.

        Args:
            query_id: Query identifier

        Returns:
            List of fact dictionaries
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM verified_facts
                WHERE query_id = %s
                ORDER BY created_at DESC
            """, (query_id,))

            return [dict(row) for row in cur.fetchall()]

    def get_facts_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Retrieve facts by status.

        Args:
            status: Status value ('success', 'error', 'timeout')

        Returns:
            List of fact dictionaries
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM verified_facts
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT 1000
            """, (status,))

            return [dict(row) for row in cur.fetchall()]

    def get_facts_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Retrieve facts in time range (uses hypertable optimization).

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of fact dictionaries
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM verified_facts
                WHERE created_at >= %s AND created_at <= %s
                ORDER BY created_at DESC
            """, (start_time, end_time))

            return [dict(row) for row in cur.fetchall()]

    def get_metrics_for_query(self, query_id: str) -> Dict[str, Any]:
        """
        Get aggregated metrics for a query.

        Args:
            query_id: Query identifier

        Returns:
            Dictionary with metrics
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total_facts,
                    AVG(execution_time_ms) as avg_execution_time_ms,
                    MAX(execution_time_ms) as max_execution_time_ms,
                    AVG(memory_used_mb) as avg_memory_mb,
                    MAX(memory_used_mb) as max_memory_mb,
                    COUNT(*) FILTER (WHERE status = 'success') as success_count,
                    COUNT(*) FILTER (WHERE status = 'error') as error_count
                FROM verified_facts
                WHERE query_id = %s
            """, (query_id,))

            row = cur.fetchone()
            return dict(row) if row else {}

    def clear_all_facts(self):
        """
        Clear all facts (for testing only).

        WARNING: Deletes all data!
        """
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE verified_facts")

        self.logger.warning("Cleared all facts (testing mode)")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")
