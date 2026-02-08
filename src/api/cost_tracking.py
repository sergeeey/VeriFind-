"""Cost tracking middleware for API calls.

Week 11 Day 4: Track LLM and data provider costs with granular metrics.

Pricing (as of 2026-02-08):
- Anthropic Claude Sonnet 4.5: $3/MTok input, $15/MTok output, $0.30/MTok cache read, $3.75/MTok cache write
- OpenAI GPT-4o: $2.50/MTok input, $10/MTok output
- DeepSeek Chat: $0.14/MTok input, $0.28/MTok output
- yfinance: Free (but track calls)
- AlphaVantage: Free tier (5 calls/min), track rate limit usage
"""

import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# Pricing constants (USD per 1M tokens)
PRICING = {
    "anthropic": {
        "claude-sonnet-4-5": {
            "input": 3.00,
            "output": 15.00,
            "cache_read": 0.30,
            "cache_write": 3.75
        },
        "claude-opus-4-6": {
            "input": 15.00,
            "output": 75.00,
            "cache_read": 1.50,
            "cache_write": 18.75
        },
        "claude-haiku-4-5": {
            "input": 0.80,
            "output": 4.00,
            "cache_read": 0.08,
            "cache_write": 1.00
        }
    },
    "openai": {
        "gpt-4o": {
            "input": 2.50,
            "output": 10.00
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60
        }
    },
    "deepseek": {
        "deepseek-chat": {
            "input": 0.14,
            "output": 0.28
        }
    }
}


class CostTracker:
    """Tracks API costs and usage metrics.

    Features:
    - LLM call tracking (Anthropic, OpenAI, DeepSeek)
    - Data provider tracking (yfinance, AlphaVantage)
    - PostgreSQL persistence
    - Prometheus metrics

    Usage:
        tracker = CostTracker(db_pool)
        await tracker.record_llm_call(
            request_id=uuid.uuid4(),
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500
        )
    """

    def __init__(self, db_pool=None, enable_metrics: bool = True):
        """Initialize cost tracker.

        Args:
            db_pool: PostgreSQL connection pool (optional for testing)
            enable_metrics: Enable Prometheus metrics
        """
        self.db_pool = db_pool
        self.enable_metrics = enable_metrics

        if enable_metrics:
            try:
                from src.monitoring.metrics import (
                    api_cost_total,
                    api_tokens_total
                )
                self.cost_metric = api_cost_total
                self.tokens_metric = api_tokens_total
            except ImportError:
                logger.warning("Metrics not available")
                self.cost_metric = None
                self.tokens_metric = None
        else:
            self.cost_metric = None
            self.tokens_metric = None

    def calculate_llm_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0
    ) -> Decimal:
        """Calculate LLM call cost in USD.

        Args:
            provider: 'anthropic', 'openai', 'deepseek'
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            cache_read_tokens: Prompt cache read tokens (Anthropic only)
            cache_write_tokens: Prompt cache write tokens (Anthropic only)

        Returns:
            Total cost in USD
        """
        pricing = PRICING.get(provider, {}).get(model)
        if not pricing:
            logger.warning(f"No pricing for {provider}/{model}, using $0")
            return Decimal("0.00")

        # Calculate cost (prices are per 1M tokens)
        cost = Decimal("0.00")

        # Input tokens
        cost += Decimal(str(input_tokens)) / Decimal("1000000") * Decimal(str(pricing["input"]))

        # Output tokens
        cost += Decimal(str(output_tokens)) / Decimal("1000000") * Decimal(str(pricing["output"]))

        # Cache tokens (Anthropic only)
        if "cache_read" in pricing and cache_read_tokens > 0:
            cost += Decimal(str(cache_read_tokens)) / Decimal("1000000") * Decimal(str(pricing["cache_read"]))

        if "cache_write" in pricing and cache_write_tokens > 0:
            cost += Decimal(str(cache_write_tokens)) / Decimal("1000000") * Decimal(str(pricing["cache_write"]))

        return cost.quantize(Decimal("0.000001"))  # Round to 6 decimal places

    async def record_llm_call(
        self,
        request_id: uuid.UUID,
        endpoint: str,
        http_method: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        user_id: Optional[str] = None,
        ticker: Optional[str] = None,
        query_type: Optional[str] = None,
        latency_ms: Optional[int] = None,
        status_code: int = 200,
        error_message: Optional[str] = None
    ) -> Decimal:
        """Record LLM API call with cost calculation.

        Args:
            request_id: Unique request identifier
            endpoint: API endpoint
            http_method: HTTP method (GET, POST, etc.)
            provider: LLM provider
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            cache_read_tokens: Cache read tokens (Anthropic)
            cache_write_tokens: Cache write tokens (Anthropic)
            user_id: Optional user identifier
            ticker: Optional stock ticker
            query_type: Optional query type
            latency_ms: Response time in milliseconds
            status_code: HTTP status code
            error_message: Error details if failed

        Returns:
            Total cost in USD
        """
        cost = self.calculate_llm_cost(
            provider, model, input_tokens, output_tokens,
            cache_read_tokens, cache_write_tokens
        )

        # Insert into database
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO api_costs (
                            request_id, endpoint, http_method, provider, model,
                            input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                            cost_usd, user_id, ticker, query_type,
                            latency_ms, status_code, error_message
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                        """,
                        str(request_id), endpoint, http_method, provider, model,
                        input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                        float(cost), user_id, ticker, query_type,
                        latency_ms, status_code, error_message
                    )
            except Exception as e:
                logger.error(f"Failed to insert cost record: {e}")

        # Update Prometheus metrics
        if self.cost_metric:
            self.cost_metric.labels(
                provider=provider,
                model=model,
                endpoint=endpoint
            ).inc(float(cost))

        if self.tokens_metric:
            self.tokens_metric.labels(
                provider=provider,
                model=model,
                token_type="input"
            ).inc(input_tokens)

            self.tokens_metric.labels(
                provider=provider,
                model=model,
                token_type="output"
            ).inc(output_tokens)

        logger.info(
            f"LLM call tracked: {provider}/{model} - "
            f"{input_tokens} in, {output_tokens} out - ${cost:.6f}"
        )

        return cost

    async def record_data_provider_call(
        self,
        request_id: uuid.UUID,
        endpoint: str,
        http_method: str,
        provider: str,
        ticker: Optional[str] = None,
        latency_ms: Optional[int] = None,
        status_code: int = 200,
        error_message: Optional[str] = None
    ) -> None:
        """Record data provider API call (yfinance, AlphaVantage).

        These are typically free but we track usage for monitoring.

        Args:
            request_id: Unique request identifier
            endpoint: API endpoint
            http_method: HTTP method
            provider: 'yfinance' or 'alpha_vantage'
            ticker: Stock ticker
            latency_ms: Response time
            status_code: HTTP status code
            error_message: Error details if failed
        """
        # Data providers are free (for now)
        cost = Decimal("0.00")

        # Insert into database
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO api_costs (
                            request_id, endpoint, http_method, provider, model,
                            input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                            cost_usd, ticker, query_type,
                            latency_ms, status_code, error_message
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        """,
                        str(request_id), endpoint, http_method, provider, None,
                        0, 0, 0, 0,
                        float(cost), ticker, "data_fetch",
                        latency_ms, status_code, error_message
                    )
            except Exception as e:
                logger.error(f"Failed to insert cost record: {e}")

        logger.info(f"Data provider call tracked: {provider} - {ticker}")

    async def get_daily_costs(
        self,
        days: int = 30
    ) -> list[Dict[str, Any]]:
        """Get daily cost summary for last N days.

        Args:
            days: Number of days to retrieve

        Returns:
            List of daily cost records
        """
        if not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    date,
                    provider,
                    model,
                    request_count,
                    total_input_tokens,
                    total_output_tokens,
                    total_cache_read_tokens,
                    total_cache_write_tokens,
                    total_cost_usd,
                    avg_latency_ms
                FROM daily_cost_summary
                WHERE date >= CURRENT_DATE - $1
                ORDER BY date DESC, total_cost_usd DESC
                """,
                days
            )

            return [dict(row) for row in rows]

    async def get_provider_breakdown(self) -> list[Dict[str, Any]]:
        """Get cost breakdown by provider (last 30 days).

        Returns:
            List of provider cost records
        """
        if not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    provider,
                    model,
                    request_count,
                    total_input_tokens,
                    total_output_tokens,
                    total_cost_usd,
                    avg_cost_per_request,
                    avg_latency_ms
                FROM provider_cost_breakdown
                """
            )

            return [dict(row) for row in rows]


class CostTrackingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic cost tracking.

    Automatically tracks costs for:
    - /api/analyze endpoints (LLM calls)
    - /api/forecast endpoints (LLM calls)
    - /api/qa endpoints (LLM calls)

    Note: Actual LLM cost recording should be done in the endpoint handler
    where token counts are available. This middleware provides the infrastructure.
    """

    def __init__(self, app: ASGIApp, cost_tracker: CostTracker):
        super().__init__(app)
        self.cost_tracker = cost_tracker

    async def dispatch(self, request: Request, call_next):
        """Process request and track costs."""
        # Generate request ID
        request_id = uuid.uuid4()
        request.state.request_id = request_id
        request.state.cost_tracker = self.cost_tracker

        # Track request start time
        start_time = time.time()

        # Process request
        response: Response = await call_next(request)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        request.state.latency_ms = latency_ms

        # Add request ID to response headers
        response.headers["X-Request-ID"] = str(request_id)

        return response
