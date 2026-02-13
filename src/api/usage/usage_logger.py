"""
Usage Tracking System for B2B API.

Week 12 Day 2: Log API requests, track costs, calculate billing.

Features:
- Request logging per API key
- LLM cost tracking (DeepSeek, Claude, GPT-4)
- TimescaleDB hypertable for efficient time-series queries
- Usage aggregation (daily, weekly, monthly)
- Quota enforcement

Usage:
    from src.api.usage.usage_logger import log_api_request

    await log_api_request(
        api_key_id=123,
        endpoint="/api/analyze-debate",
        method="POST",
        status_code=200,
        response_time_ms=3500,
        cost_usd=0.0020,
        tokens_used=1500,
        llm_provider="multi-llm"
    )
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from sqlalchemy import (
    Table, Column, Integer, String, Float, DateTime, Boolean,
    MetaData, select, func, and_, text, PrimaryKeyConstraint, Sequence
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
import os


logger = logging.getLogger(__name__)


# Usage Logs Schema (TimescaleDB Hypertable)
metadata = MetaData()

api_usage_logs = Table(
    'api_usage_logs',
    metadata,
    # NOTE: For TimescaleDB hypertables, no primary key constraint
    # Using Sequence for id generation since autoincrement doesn't work without primary key
    Column('id', Integer, Sequence('api_usage_logs_id_seq'), server_default=text("nextval('api_usage_logs_id_seq')")),
    Column('timestamp', DateTime, default=datetime.utcnow, nullable=False, index=True),
    Column('api_key_id', Integer, nullable=False, index=True),
    Column('customer_name', String(255), nullable=False),
    Column('tier', String(50), nullable=False),
    Column('endpoint', String(255), nullable=False),
    Column('method', String(10), nullable=False),  # GET, POST, etc.
    Column('status_code', Integer, nullable=False),
    Column('response_time_ms', Integer, nullable=False),
    Column('cost_usd', Float, nullable=False, default=0.0),
    Column('tokens_used', Integer, nullable=True),
    Column('llm_provider', String(100), nullable=True),  # deepseek, anthropic, openai, multi-llm
    Column('error_message', String(1000), nullable=True),
    Column('user_agent', String(500), nullable=True),
    Column('ip_address', String(45), nullable=True)  # IPv6 = 45 chars max
)


class UsageLogger:
    """
    Usage logging and billing system.

    Logs all API requests for tracking, billing, and analytics.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize Usage Logger.

        Args:
            db_url: Database URL (defaults to TIMESCALEDB_URL from env)
        """
        self.db_url = db_url or os.getenv(
            "TIMESCALEDB_ASYNC_URL",
            "postgresql+asyncpg://ape_test:test_password_123@localhost:5433/ape_timeseries"
        )
        self.engine: Optional[AsyncEngine] = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize database connection and create hypertable."""
        if self.engine is None:
            self.engine = create_async_engine(self.db_url, echo=False)

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(metadata.create_all)

                # Convert to hypertable for time-series optimization
                await conn.execute(text("""
                    SELECT create_hypertable(
                        'api_usage_logs',
                        'timestamp',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    );
                """))

                # Create index for efficient queries
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_usage_api_key_timestamp
                    ON api_usage_logs (api_key_id, timestamp DESC);
                """))

            self.logger.info("Usage Logger initialized with hypertable")

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            self.logger.info("Usage Logger closed")

    async def log_request(
        self,
        api_key_id: int,
        customer_name: str,
        tier: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        cost_usd: float = 0.0,
        tokens_used: Optional[int] = None,
        llm_provider: Optional[str] = None,
        error_message: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log API request.

        Args:
            api_key_id: API key ID from api_keys table
            customer_name: Customer name
            tier: Subscription tier
            endpoint: API endpoint (e.g., "/api/analyze-debate")
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            cost_usd: Cost in USD (LLM costs)
            tokens_used: Number of tokens used
            llm_provider: LLM provider (deepseek, anthropic, openai, multi-llm)
            error_message: Error message if request failed
            user_agent: User agent string
            ip_address: Client IP address
        """
        if self.engine is None:
            await self.initialize()

        async with self.engine.begin() as conn:
            await conn.execute(
                api_usage_logs.insert().values(
                    timestamp=datetime.utcnow(),
                    api_key_id=api_key_id,
                    customer_name=customer_name,
                    tier=tier,
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    cost_usd=cost_usd,
                    tokens_used=tokens_used,
                    llm_provider=llm_provider,
                    error_message=error_message,
                    user_agent=user_agent,
                    ip_address=ip_address
                )
            )

        self.logger.debug(
            f"Logged request: {customer_name} {method} {endpoint} "
            f"({status_code}) ${cost_usd:.4f}"
        )

    async def get_usage_stats(
        self,
        api_key_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics.

        Args:
            api_key_id: Filter by API key ID (None = all keys)
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: now)

        Returns:
            Usage statistics dict
        """
        if self.engine is None:
            await self.initialize()

        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()

        # Build query
        query = select(
            func.count(api_usage_logs.c.id).label('total_requests'),
            func.sum(api_usage_logs.c.cost_usd).label('total_cost_usd'),
            func.sum(api_usage_logs.c.tokens_used).label('total_tokens'),
            func.avg(api_usage_logs.c.response_time_ms).label('avg_response_time_ms'),
            func.count(
                func.nullif(api_usage_logs.c.status_code >= 500, False)
            ).label('error_count')
        ).where(
            and_(
                api_usage_logs.c.timestamp >= start_date,
                api_usage_logs.c.timestamp <= end_date
            )
        )

        if api_key_id is not None:
            query = query.where(api_usage_logs.c.api_key_id == api_key_id)

        async with self.engine.connect() as conn:
            result = await conn.execute(query)
            row = result.fetchone()

            if not row:
                return {
                    'total_requests': 0,
                    'total_cost_usd': 0.0,
                    'total_tokens': 0,
                    'avg_response_time_ms': 0.0,
                    'error_count': 0
                }

            return {
                'total_requests': row.total_requests or 0,
                'total_cost_usd': float(row.total_cost_usd or 0.0),
                'total_tokens': row.total_tokens or 0,
                'avg_response_time_ms': float(row.avg_response_time_ms or 0.0),
                'error_count': row.error_count or 0,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }

    async def get_daily_usage(
        self,
        api_key_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily usage breakdown.

        Args:
            api_key_id: API key ID
            days: Number of days to retrieve

        Returns:
            List of daily usage dicts
        """
        if self.engine is None:
            await self.initialize()

        start_date = datetime.utcnow() - timedelta(days=days)

        # Create labeled expression for date truncation
        date_trunc_expr = func.date_trunc('day', api_usage_logs.c.timestamp).label('date')

        query = select(
            date_trunc_expr,
            func.count(api_usage_logs.c.id).label('requests'),
            func.sum(api_usage_logs.c.cost_usd).label('cost_usd'),
            func.sum(api_usage_logs.c.tokens_used).label('tokens')
        ).where(
            and_(
                api_usage_logs.c.api_key_id == api_key_id,
                api_usage_logs.c.timestamp >= start_date
            )
        ).group_by(
            # Group only by the truncated date expression
            date_trunc_expr
        ).order_by(
            date_trunc_expr.desc()
        )

        async with self.engine.connect() as conn:
            result = await conn.execute(query)

            return [
                {
                    'date': row.date.isoformat(),
                    'requests': row.requests,
                    'cost_usd': float(row.cost_usd or 0.0),
                    'tokens': row.tokens or 0
                }
                for row in result.fetchall()
            ]

    async def get_current_month_usage(
        self,
        api_key_id: int
    ) -> Dict[str, Any]:
        """
        Get current month usage (for quota enforcement).

        Args:
            api_key_id: API key ID

        Returns:
            Current month usage dict
        """
        if self.engine is None:
            await self.initialize()

        # Start of current month
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        return await self.get_usage_stats(
            api_key_id=api_key_id,
            start_date=month_start,
            end_date=now
        )

    async def check_quota(
        self,
        api_key_id: int,
        monthly_quota: Optional[int]
    ) -> tuple[bool, int, int]:
        """
        Check if API key has exceeded quota.

        Args:
            api_key_id: API key ID
            monthly_quota: Monthly request quota (None = unlimited)

        Returns:
            Tuple of (within_quota, requests_used, requests_remaining)
        """
        if monthly_quota is None:
            return True, 0, float('inf')  # Unlimited

        usage = await self.get_current_month_usage(api_key_id)
        requests_used = usage['total_requests']
        requests_remaining = max(0, monthly_quota - requests_used)

        within_quota = requests_used < monthly_quota

        return within_quota, requests_used, requests_remaining


# Global instance
_usage_logger: Optional[UsageLogger] = None


async def get_usage_logger() -> UsageLogger:
    """Get or create global UsageLogger instance."""
    global _usage_logger
    if _usage_logger is None:
        _usage_logger = UsageLogger()
        await _usage_logger.initialize()
    return _usage_logger


# ============================================================================
# Cost Calculator
# ============================================================================

class CostCalculator:
    """
    Calculate costs for LLM API requests.

    Pricing (as of 2026 Q1):
    - DeepSeek-V3: $0.27/M input, $1.10/M output
    - Claude Sonnet 4.5: $3.00/M input, $15.00/M output
    - GPT-4 Turbo: $10.00/M input, $30.00/M output
    """

    # Pricing per million tokens (USD)
    PRICING = {
        'deepseek': {
            'input': 0.27,
            'output': 1.10
        },
        'anthropic': {
            'input': 3.00,
            'output': 15.00
        },
        'openai': {
            'input': 10.00,
            'output': 30.00
        }
    }

    @staticmethod
    def calculate_cost(
        provider: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for LLM API call.

        Args:
            provider: LLM provider (deepseek, anthropic, openai)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = CostCalculator.PRICING.get(provider.lower())

        if not pricing:
            logger.warning(f"Unknown provider: {provider}, assuming $0 cost")
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        total_cost = input_cost + output_cost

        return round(total_cost, 6)  # Round to 6 decimal places

    @staticmethod
    def calculate_multi_llm_cost(
        bull_tokens: tuple[int, int],  # (input, output)
        bear_tokens: tuple[int, int],
        arbiter_tokens: tuple[int, int]
    ) -> Dict[str, float]:
        """
        Calculate cost for Multi-LLM Debate.

        Args:
            bull_tokens: Bull agent (DeepSeek) tokens
            bear_tokens: Bear agent (Claude) tokens
            arbiter_tokens: Arbiter agent (GPT-4) tokens

        Returns:
            Cost breakdown dict
        """
        bull_cost = CostCalculator.calculate_cost('deepseek', *bull_tokens)
        bear_cost = CostCalculator.calculate_cost('anthropic', *bear_tokens)
        arbiter_cost = CostCalculator.calculate_cost('openai', *arbiter_tokens)

        total_cost = bull_cost + bear_cost + arbiter_cost

        return {
            'bull_cost_usd': bull_cost,
            'bear_cost_usd': bear_cost,
            'arbiter_cost_usd': arbiter_cost,
            'total_cost_usd': round(total_cost, 6)
        }
