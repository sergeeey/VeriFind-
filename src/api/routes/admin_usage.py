"""
Admin API endpoints for Usage Tracking and Billing.

Week 12 Day 2-3: View usage statistics, billing data, quotas.

Endpoints:
- GET /admin/usage/stats - Get overall usage statistics
- GET /admin/usage/by-customer - Get usage by customer
- GET /admin/usage/daily - Get daily usage breakdown
- GET /admin/usage/billing - Get billing summary
- GET /admin/usage/top-customers - Get top customers by usage/cost
"""

from fastapi import APIRouter, HTTPException, status, Header, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from src.api.usage.usage_logger import get_usage_logger
from src.api.auth.api_key_manager import get_api_key_manager


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/usage", tags=["Admin - Usage & Billing"])


# ============================================================================
# Admin Authentication (reuse from admin_api_keys.py)
# ============================================================================

async def require_admin_secret(
    x_admin_secret: Optional[str] = Header(None, description="Admin Secret")
):
    """Require admin secret for admin endpoints."""
    import os
    admin_secret = os.getenv("ADMIN_SECRET")

    if not admin_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication not configured"
        )

    if not x_admin_secret or x_admin_secret != admin_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin secret",
            headers={"WWW-Authenticate": "AdminSecret"}
        )

    return True


# ============================================================================
# Response Models
# ============================================================================

class UsageStatsResponse(BaseModel):
    """Response model for usage statistics."""
    total_requests: int
    total_cost_usd: float
    total_tokens: int
    avg_response_time_ms: float
    error_count: int
    start_date: str
    end_date: str


class DailyUsageResponse(BaseModel):
    """Response model for daily usage."""
    date: str
    requests: int
    cost_usd: float
    tokens: int


class CustomerUsageResponse(BaseModel):
    """Response model for customer usage."""
    customer_name: str
    tier: str
    total_requests: int
    total_cost_usd: float
    quota_used_percent: Optional[float]


class BillingSummaryResponse(BaseModel):
    """Response model for billing summary."""
    period_start: str
    period_end: str
    total_revenue_usd: float
    total_requests: int
    avg_cost_per_request: float
    customers_billed: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/stats",
    response_model=UsageStatsResponse,
    summary="Get overall usage statistics"
)
async def get_usage_stats(
    start_date: Optional[datetime] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: now)"),
    api_key_id: Optional[int] = Query(None, description="Filter by API key ID"),
    _admin: bool = Depends(require_admin_secret)
):
    """
    Get overall usage statistics.

    Args:
        start_date: Start date for stats (default: 30 days ago)
        end_date: End date for stats (default: now)
        api_key_id: Filter by specific API key (optional)

    Returns:
        Usage statistics
    """
    usage_logger = await get_usage_logger()

    try:
        stats = await usage_logger.get_usage_stats(
            api_key_id=api_key_id,
            start_date=start_date,
            end_date=end_date
        )

        return UsageStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage stats: {str(e)}"
        )


@router.get(
    "/daily",
    response_model=List[DailyUsageResponse],
    summary="Get daily usage breakdown"
)
async def get_daily_usage(
    api_key_id: int = Query(..., description="API key ID"),
    days: int = Query(30, description="Number of days to retrieve"),
    _admin: bool = Depends(require_admin_secret)
):
    """
    Get daily usage breakdown for an API key.

    Args:
        api_key_id: API key ID
        days: Number of days to retrieve (default: 30)

    Returns:
        List of daily usage records
    """
    usage_logger = await get_usage_logger()

    try:
        daily_usage = await usage_logger.get_daily_usage(
            api_key_id=api_key_id,
            days=days
        )

        return [DailyUsageResponse(**day) for day in daily_usage]

    except Exception as e:
        logger.error(f"Failed to get daily usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily usage: {str(e)}"
        )


@router.get(
    "/by-customer",
    response_model=List[CustomerUsageResponse],
    summary="Get usage by customer"
)
async def get_usage_by_customer(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    _admin: bool = Depends(require_admin_secret)
):
    """
    Get usage statistics grouped by customer.

    Args:
        start_date: Start date (default: 30 days ago)
        end_date: End date (default: now)

    Returns:
        List of customer usage records
    """
    key_manager = await get_api_key_manager()
    usage_logger = await get_usage_logger()

    try:
        # Get all API keys
        all_keys = await key_manager.list_api_keys(limit=1000)

        customer_usage = []

        for key in all_keys:
            # Get usage for this key
            stats = await usage_logger.get_usage_stats(
                api_key_id=key['id'],
                start_date=start_date,
                end_date=end_date
            )

            # Calculate quota used percent
            quota_used_percent = None
            if key['monthly_quota']:
                month_stats = await usage_logger.get_current_month_usage(key['id'])
                quota_used_percent = (month_stats['total_requests'] / key['monthly_quota']) * 100

            customer_usage.append(CustomerUsageResponse(
                customer_name=key['customer_name'],
                tier=key['tier'],
                total_requests=stats['total_requests'],
                total_cost_usd=stats['total_cost_usd'],
                quota_used_percent=quota_used_percent
            ))

        # Sort by total cost descending
        customer_usage.sort(key=lambda x: x.total_cost_usd, reverse=True)

        return customer_usage

    except Exception as e:
        logger.error(f"Failed to get usage by customer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage by customer: {str(e)}"
        )


@router.get(
    "/billing",
    response_model=BillingSummaryResponse,
    summary="Get billing summary"
)
async def get_billing_summary(
    start_date: Optional[datetime] = Query(None, description="Start date (default: current month)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: now)"),
    _admin: bool = Depends(require_admin_secret)
):
    """
    Get billing summary for a period.

    Args:
        start_date: Start date (default: start of current month)
        end_date: End date (default: now)

    Returns:
        Billing summary
    """
    usage_logger = await get_usage_logger()
    key_manager = await get_api_key_manager()

    try:
        # Default to current month
        if start_date is None:
            now = datetime.utcnow()
            start_date = datetime(now.year, now.month, 1)
        if end_date is None:
            end_date = datetime.utcnow()

        # Get overall stats
        stats = await usage_logger.get_usage_stats(
            start_date=start_date,
            end_date=end_date
        )

        # Count unique customers
        all_keys = await key_manager.list_api_keys(limit=1000)
        customers_billed = len(set(k['customer_name'] for k in all_keys))

        # Calculate average cost per request
        avg_cost_per_request = 0.0
        if stats['total_requests'] > 0:
            avg_cost_per_request = stats['total_cost_usd'] / stats['total_requests']

        return BillingSummaryResponse(
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            total_revenue_usd=stats['total_cost_usd'],
            total_requests=stats['total_requests'],
            avg_cost_per_request=round(avg_cost_per_request, 6),
            customers_billed=customers_billed
        )

    except Exception as e:
        logger.error(f"Failed to get billing summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing summary: {str(e)}"
        )


@router.get(
    "/top-customers",
    response_model=List[CustomerUsageResponse],
    summary="Get top customers by usage/cost"
)
async def get_top_customers(
    limit: int = Query(10, description="Number of top customers to return"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    _admin: bool = Depends(require_admin_secret)
):
    """
    Get top customers by usage or cost.

    Args:
        limit: Number of top customers to return (default: 10)
        start_date: Start date (default: 30 days ago)
        end_date: End date (default: now)

    Returns:
        List of top customer usage records
    """
    # Reuse get_usage_by_customer logic
    customer_usage = await get_usage_by_customer(
        start_date=start_date,
        end_date=end_date,
        _admin=True
    )

    # Already sorted by cost descending, just limit
    return customer_usage[:limit]


@router.get(
    "/quota-status",
    summary="Get quota status for all customers"
)
async def get_quota_status(
    _admin: bool = Depends(require_admin_secret)
):
    """
    Get quota status for all customers (current month).

    Returns:
        List of quota status records
    """
    key_manager = await get_api_key_manager()
    usage_logger = await get_usage_logger()

    try:
        all_keys = await key_manager.list_api_keys(limit=1000, is_active=True)

        quota_status = []

        for key in all_keys:
            if key['monthly_quota'] is None:
                continue  # Skip unlimited keys

            # Check quota
            within_quota, used, remaining = await usage_logger.check_quota(
                api_key_id=key['id'],
                monthly_quota=key['monthly_quota']
            )

            quota_status.append({
                'customer_name': key['customer_name'],
                'tier': key['tier'],
                'monthly_quota': key['monthly_quota'],
                'requests_used': used,
                'requests_remaining': remaining,
                'usage_percent': round((used / key['monthly_quota']) * 100, 2),
                'within_quota': within_quota
            })

        # Sort by usage percent descending (show highest usage first)
        quota_status.sort(key=lambda x: x['usage_percent'], reverse=True)

        return quota_status

    except Exception as e:
        logger.error(f"Failed to get quota status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota status: {str(e)}"
        )
