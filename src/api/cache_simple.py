"""
Simple Route-Level Cache for APE 2026
Week 10 - Fast alternative to middleware caching

Usage:
    from src.api.cache_simple import cached_analyze
    
    @cached_analyze(ttl_seconds=300)
    async def analyze_query(...) -> AnalysisResponse:
        ...
"""

import hashlib
import json
import functools
from datetime import datetime, timedelta
from typing import Callable, Optional

import redis.asyncio as redis
from fastapi import Request

from .config import get_settings

settings = get_settings()

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def generate_cache_key(request: Request, body: dict) -> str:
    """Generate cache key from request."""
    key_parts = [
        request.method,
        str(request.url.path),
        json.dumps(body, sort_keys=True)
    ]
    key_string = "|".join(key_parts)
    return f"ape:simple:{hashlib.sha256(key_string.encode()).hexdigest()[:32]}"


async def get_cached_response(cache_key: str) -> Optional[dict]:
    """Get cached response from Redis."""
    if not settings.cache_enabled:
        return None
    
    try:
        r = await get_redis()
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    
    return None


async def set_cached_response(cache_key: str, data: dict, ttl_seconds: int = 300):
    """Cache response in Redis."""
    if not settings.cache_enabled:
        return
    
    try:
        r = await get_redis()
        await r.setex(cache_key, ttl_seconds, json.dumps(data))
    except Exception:
        pass


class CachedAnalyze:
    """
    Simple caching for analyze endpoint.
    
    Usage in route:
        cache = CachedAnalyze()
        
        @router.post("/analyze")
        async def analyze(request: Request, body: QueryRequest):
            # Check cache
            cached = await cache.get(request, body)
            if cached:
                return AnalysisResponse(**cached, cache_hit=True)
            
            # Process...
            result = await process(...)
            
            # Cache result
            await cache.set(request, body, result.dict())
            return result
    """
    
    async def get(self, request: Request, body) -> Optional[dict]:
        """Get cached result."""
        cache_key = generate_cache_key(request, body.dict() if hasattr(body, 'dict') else body)
        return await get_cached_response(cache_key)
    
    async def set(self, request: Request, body, result: dict, ttl: int = 300):
        """Cache result."""
        cache_key = generate_cache_key(request, body.dict() if hasattr(body, 'dict') else body)
        await set_cached_response(cache_key, result, ttl)


# Global instance
analyze_cache = CachedAnalyze()
