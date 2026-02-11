"""
Admin API endpoints for API Key management.

Week 12 Day 1: CRUD operations for API keys.

Endpoints:
- POST /admin/api-keys - Create new API key
- GET /admin/api-keys - List API keys
- GET /admin/api-keys/{key_prefix} - Get key details
- DELETE /admin/api-keys/{key_prefix} - Revoke API key

Note: These endpoints should be protected by admin authentication in production.
For MVP, we use a simple ADMIN_SECRET environment variable.
"""

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import os
import logging

from src.api.auth.api_key_manager import get_api_key_manager


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/api-keys", tags=["Admin - API Keys"])


# ============================================================================
# Admin Authentication
# ============================================================================

async def require_admin_secret(
    x_admin_secret: Optional[str] = Header(None, description="Admin Secret")
):
    """
    Dependency: Require admin secret for admin endpoints.

    In production, replace with proper admin authentication (OAuth, JWT, etc.).
    """
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
# Request/Response Models
# ============================================================================

class CreateAPIKeyRequest(BaseModel):
    """Request model for creating API key."""
    customer_name: str = Field(..., description="Customer/company name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    tier: str = Field("free", description="Subscription tier (free, pro, enterprise)")
    rate_limit_per_hour: int = Field(100, description="Max requests per hour")
    monthly_quota: Optional[int] = Field(10000, description="Max requests per month (null = unlimited)")
    expires_in_days: Optional[int] = Field(None, description="Days until expiration (null = never)")
    metadata: Optional[str] = Field(None, description="Additional JSON metadata")


class APIKeyResponse(BaseModel):
    """Response model for API key creation."""
    api_key: str = Field(..., description="Plain API key (SAVE THIS - won't be shown again!)")
    key_prefix: str = Field(..., description="Key prefix for identification")
    customer_name: str
    tier: str
    rate_limit_per_hour: int
    monthly_quota: Optional[int]
    created_at: datetime
    expires_at: Optional[datetime]


class APIKeyInfo(BaseModel):
    """Response model for API key information."""
    id: int
    key_prefix: str
    customer_name: str
    customer_email: Optional[str]
    tier: str
    is_active: bool
    rate_limit_per_hour: int
    monthly_quota: Optional[int]
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    metadata: Optional[str]


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new API key"
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    _admin: bool = Depends(require_admin_secret)
):
    """
    Create new API key for B2B customer.

    **Important:** The plain API key is returned ONLY once.
    Save it securely - it cannot be retrieved later.

    Args:
        request: API key creation parameters

    Returns:
        API key and metadata

    Raises:
        500: If database error occurs
    """
    manager = await get_api_key_manager()

    try:
        api_key, key_record = await manager.create_api_key(
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            tier=request.tier,
            rate_limit_per_hour=request.rate_limit_per_hour,
            monthly_quota=request.monthly_quota,
            expires_in_days=request.expires_in_days,
            metadata=request.metadata
        )

        logger.info(
            f"Admin created API key for {request.customer_name} "
            f"(tier={request.tier})"
        )

        return APIKeyResponse(
            api_key=api_key,
            key_prefix=key_record['key_prefix'],
            customer_name=key_record['customer_name'],
            tier=key_record['tier'],
            rate_limit_per_hour=key_record['rate_limit_per_hour'],
            monthly_quota=key_record['monthly_quota'],
            created_at=key_record['created_at'],
            expires_at=key_record['expires_at']
        )

    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get(
    "",
    response_model=List[APIKeyInfo],
    summary="List API keys"
)
async def list_api_keys(
    customer_name: Optional[str] = None,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    _admin: bool = Depends(require_admin_secret)
):
    """
    List API keys with optional filters.

    Args:
        customer_name: Filter by customer name (partial match)
        tier: Filter by tier (free, pro, enterprise)
        is_active: Filter by active status
        limit: Maximum records to return (default: 100)

    Returns:
        List of API key metadata (hashed keys, no plain keys)
    """
    manager = await get_api_key_manager()

    try:
        keys = await manager.list_api_keys(
            customer_name=customer_name,
            tier=tier,
            is_active=is_active,
            limit=limit
        )

        return [
            APIKeyInfo(
                id=k['id'],
                key_prefix=k['key_prefix'],
                customer_name=k['customer_name'],
                customer_email=k['customer_email'],
                tier=k['tier'],
                is_active=k['is_active'],
                rate_limit_per_hour=k['rate_limit_per_hour'],
                monthly_quota=k['monthly_quota'],
                created_at=k['created_at'],
                last_used_at=k['last_used_at'],
                expires_at=k['expires_at'],
                metadata=k['metadata']
            )
            for k in keys
        ]

    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.delete(
    "/{key_prefix}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key"
)
async def revoke_api_key(
    key_prefix: str,
    _admin: bool = Depends(require_admin_secret)
):
    """
    Revoke (deactivate) API key by prefix.

    The API key will be marked as inactive and can no longer be used.
    This operation is reversible (can be reactivated manually in DB).

    Args:
        key_prefix: Key prefix (e.g., "sk-ape-a1b2c3d4")

    Raises:
        404: If key not found
        500: If database error occurs
    """
    manager = await get_api_key_manager()

    try:
        # Revoke key by prefix
        revoked = await manager.revoke_by_prefix(key_prefix)

        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key with prefix {key_prefix} not found"
            )

        logger.info(f"Admin revoked API key: {key_prefix}")
        return  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )


@router.get(
    "/stats",
    summary="Get API key statistics"
)
async def get_api_key_stats(
    _admin: bool = Depends(require_admin_secret)
):
    """
    Get aggregate statistics about API keys.

    Returns:
        Statistics including total keys, active keys, keys by tier, etc.
    """
    manager = await get_api_key_manager()

    try:
        all_keys = await manager.list_api_keys(limit=10000)

        stats = {
            "total_keys": len(all_keys),
            "active_keys": len([k for k in all_keys if k['is_active']]),
            "inactive_keys": len([k for k in all_keys if not k['is_active']]),
            "keys_by_tier": {
                "free": len([k for k in all_keys if k['tier'] == 'free']),
                "pro": len([k for k in all_keys if k['tier'] == 'pro']),
                "enterprise": len([k for k in all_keys if k['tier'] == 'enterprise'])
            },
            "keys_with_usage": len([k for k in all_keys if k['last_used_at'] is not None]),
            "never_used_keys": len([k for k in all_keys if k['last_used_at'] is None])
        }

        return stats

    except Exception as e:
        logger.error(f"Failed to get API key stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )
