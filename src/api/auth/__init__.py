"""
API Authentication Module.

Week 12 Day 1: API key management and validation.
"""

from .api_key_manager import (
    APIKeyManager,
    get_api_key_manager,
    api_keys_table
)
from .middleware import (
    get_api_key_from_request,
    require_api_key,
    require_tier
)

__all__ = [
    "APIKeyManager",
    "get_api_key_manager",
    "api_keys_table",
    "get_api_key_from_request",
    "require_api_key",
    "require_tier"
]
