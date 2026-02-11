"""
FastAPI Middleware for API Key Validation.

Week 12 Day 1: Dependencies and middleware for API key authentication.

Usage:
    from src.api.auth.middleware import require_api_key

    @app.get("/api/protected-endpoint")
    async def protected_endpoint(api_key_info: dict = Depends(require_api_key)):
        # api_key_info contains customer_name, tier, rate_limit, etc.
        return {"message": "Authenticated!", "customer": api_key_info["customer_name"]}
"""

from fastapi import Header, HTTPException, status, Depends
from typing import Optional, Dict, Any, List
import logging

from .api_key_manager import get_api_key_manager


logger = logging.getLogger(__name__)


async def get_api_key_from_request(
    x_api_key: Optional[str] = Header(None, description="API Key")
) -> Optional[str]:
    """
    Extract API key from request headers.

    Looks for X-API-Key header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        API key string or None
    """
    return x_api_key


async def require_api_key(
    api_key: Optional[str] = Depends(get_api_key_from_request)
) -> Dict[str, Any]:
    """
    Dependency: Require valid API key.

    Validates API key and returns key information.
    Raises HTTPException if invalid.

    Args:
        api_key: API key from header

    Returns:
        API key information dict

    Raises:
        HTTPException: 401 if no API key provided
        HTTPException: 403 if API key invalid or inactive
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Validate API key
    manager = await get_api_key_manager()
    is_valid = await manager.validate_api_key(api_key, update_last_used=True)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive API key"
        )

    # Get key info
    key_info = await manager.get_key_info(api_key)

    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key not found"
        )

    logger.info(
        f"Authenticated request from {key_info['customer_name']} "
        f"(tier={key_info['tier']}, prefix={key_info['key_prefix']})"
    )

    return key_info


def require_tier(allowed_tiers: List[str]):
    """
    Dependency factory: Require specific tier(s).

    Args:
        allowed_tiers: List of allowed tiers (e.g., ["pro", "enterprise"])

    Returns:
        FastAPI dependency function

    Example:
        @app.get("/api/premium-endpoint")
        async def premium_endpoint(
            api_key_info: dict = Depends(require_tier(["pro", "enterprise"]))
        ):
            return {"message": "Premium feature"}
    """
    async def tier_checker(
        api_key_info: Dict[str, Any] = Depends(require_api_key)
    ) -> Dict[str, Any]:
        """Check if API key tier is allowed."""
        if api_key_info['tier'] not in allowed_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {' or '.join(allowed_tiers)} tier"
            )
        return api_key_info

    return tier_checker


async def optional_api_key(
    api_key: Optional[str] = Depends(get_api_key_from_request)
) -> Optional[Dict[str, Any]]:
    """
    Dependency: Optional API key.

    If API key provided, validates it and returns key info.
    If no API key, returns None (allows anonymous access).

    Args:
        api_key: API key from header

    Returns:
        API key information dict or None

    Raises:
        HTTPException: 403 if API key provided but invalid
    """
    if not api_key:
        return None

    # Validate API key
    manager = await get_api_key_manager()
    is_valid = await manager.validate_api_key(api_key, update_last_used=True)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive API key"
        )

    # Get key info
    key_info = await manager.get_key_info(api_key)

    return key_info
