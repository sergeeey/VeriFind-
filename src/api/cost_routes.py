"""Cost tracking API routes.

Week 11 Day 4: API endpoints for cost monitoring and analytics.

Endpoints:
- GET /api/costs/daily - Daily cost summary
- GET /api/costs/providers - Provider cost breakdown
- GET /api/costs/total - Total costs (today, week, month)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from .cost_tracking import CostTracker

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/costs", tags=["Costs"])


# ============================================================================
# Response Models
# ============================================================================

class DailyCostRecord(BaseModel):
    """Daily cost record."""
    date: date = Field(..., description="Date")
    provider: str = Field(..., description="Provider name")
    model: Optional[str] = Field(None, description="Model name (NULL for data providers)")
    request_count: int = Field(..., description="Number of requests")
    total_input_tokens: int = Field(..., description="Total input tokens")
    total_output_tokens: int = Field(..., description="Total output tokens")
    total_cache_read_tokens: int = Field(..., description="Total cache read tokens")
    total_cache_write_tokens: int = Field(..., description="Total cache write tokens")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    avg_latency_ms: Optional[float] = Field(None, description="Average latency in ms")


class ProviderCostRecord(BaseModel):
    """Provider cost breakdown."""
    provider: str = Field(..., description="Provider name")
    model: Optional[str] = Field(None, description="Model name")
    request_count: int = Field(..., description="Number of requests")
    total_input_tokens: int = Field(..., description="Total input tokens")
    total_output_tokens: int = Field(..., description="Total output tokens")
    total_cost_usd: float = Field(..., description="Total cost in USD (last 30 days)")
    avg_cost_per_request: float = Field(..., description="Average cost per request")
    avg_latency_ms: Optional[float] = Field(None, description="Average latency in ms")


class TotalCostsResponse(BaseModel):
    """Total costs for different periods."""
    today_usd: float = Field(..., description="Today's costs")
    week_usd: float = Field(..., description="This week's costs")
    month_usd: float = Field(..., description="This month's costs")
    total_requests_today: int = Field(..., description="Total requests today")
    total_requests_week: int = Field(..., description="Total requests this week")
    total_requests_month: int = Field(..., description="Total requests this month")
    breakdown: List[ProviderCostRecord] = Field(..., description="Cost breakdown by provider")


# ============================================================================
# Dependency Injection
# ============================================================================

_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get CostTracker instance.

    Returns:
        CostTracker instance

    Raises:
        HTTPException: If cost tracker not initialized
    """
    global _cost_tracker
    if _cost_tracker is None:
        raise HTTPException(
            status_code=503,
            detail="Cost tracking not initialized"
        )
    return _cost_tracker


def initialize_cost_tracker(db_pool=None, enable_metrics: bool = True):
    """Initialize global cost tracker.

    Args:
        db_pool: PostgreSQL connection pool
        enable_metrics: Enable Prometheus metrics
    """
    global _cost_tracker
    _cost_tracker = CostTracker(db_pool=db_pool, enable_metrics=enable_metrics)
    logger.info("Cost tracker initialized")


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/daily", response_model=List[DailyCostRecord])
async def get_daily_costs(
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    cost_tracker: CostTracker = Depends(get_cost_tracker)
):
    """Get daily cost summary for last N days.

    Args:
        days: Number of days (1-365)

    Returns:
        List of daily cost records sorted by date (newest first)

    Example:
        GET /api/costs/daily?days=7

        Returns last 7 days of costs broken down by provider and model.
    """
    try:
        records = await cost_tracker.get_daily_costs(days=days)
        return records
    except Exception as e:
        logger.error(f"Failed to retrieve daily costs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve costs")


@router.get("/providers", response_model=List[ProviderCostRecord])
async def get_provider_breakdown(
    cost_tracker: CostTracker = Depends(get_cost_tracker)
):
    """Get cost breakdown by provider (last 30 days).

    Returns:
        List of provider cost records sorted by total cost (highest first)

    Example:
        GET /api/costs/providers

        Returns cost breakdown showing:
        - Anthropic (Claude Sonnet 4.5): $12.45
        - OpenAI (GPT-4o): $5.23
        - DeepSeek (deepseek-chat): $0.87
    """
    try:
        records = await cost_tracker.get_provider_breakdown()
        return records
    except Exception as e:
        logger.error(f"Failed to retrieve provider breakdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve costs")


@router.get("/total", response_model=TotalCostsResponse)
async def get_total_costs(
    cost_tracker: CostTracker = Depends(get_cost_tracker)
):
    """Get total costs for today, this week, and this month.

    Returns:
        TotalCostsResponse with aggregated costs and request counts

    Example:
        GET /api/costs/total

        Returns:
        {
            "today_usd": 2.45,
            "week_usd": 15.78,
            "month_usd": 67.32,
            "total_requests_today": 150,
            "total_requests_week": 980,
            "total_requests_month": 4200,
            "breakdown": [...]
        }
    """
    try:
        # Get last 30 days of data
        daily_costs = await cost_tracker.get_daily_costs(days=30)

        # Calculate totals
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday
        month_start = today.replace(day=1)

        today_usd = 0.0
        week_usd = 0.0
        month_usd = 0.0
        today_requests = 0
        week_requests = 0
        month_requests = 0

        for record in daily_costs:
            record_date = record["date"]
            cost = float(record["total_cost_usd"])
            requests = record["request_count"]

            if record_date == today:
                today_usd += cost
                today_requests += requests

            if record_date >= week_start:
                week_usd += cost
                week_requests += requests

            if record_date >= month_start:
                month_usd += cost
                month_requests += requests

        # Get provider breakdown
        breakdown = await cost_tracker.get_provider_breakdown()

        return TotalCostsResponse(
            today_usd=today_usd,
            week_usd=week_usd,
            month_usd=month_usd,
            total_requests_today=today_requests,
            total_requests_week=week_requests,
            total_requests_month=month_requests,
            breakdown=breakdown
        )
    except Exception as e:
        logger.error(f"Failed to calculate total costs: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate costs")
