"""
Response Cache Middleware for APE 2026
Week 10 - Performance Optimization

Provides intelligent caching with Redis for API responses.
Expected impact:
- 80% cache hit rate for repeated queries
- 95% latency reduction on cache hits
- Cost savings: ~$0.0005 per cached query
"""

import hashlib
import json
from datetime import timedelta
from typing import Optional

import redis.asyncio as redis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Cache API responses with intelligent invalidation."""
    
    def __init__(self, app, redis_url: str = "redis://localhost:6380"):
        super().__init__(app)
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.cache_ttl = timedelta(minutes=5)  # 5 minute cache
        
    async def dispatch(self, request: Request, call_next):
        # Only cache GET and POST /api/analyze
        if request.method not in ["GET", "POST"]:
            return await call_next(request)
            
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Skip cache for certain endpoints
        skip_paths = ["/api/health", "/api/status", "/docs", "/redoc", "/openapi.json"]
        if any(request.url.path.startswith(p) for p in skip_paths):
            return await call_next(request)
        
        # Generate cache key
        cache_key = await self._generate_cache_key(request)
        
        # Check cache
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                # Add cache header
                headers = data.get("headers", {})
                headers["X-Cache"] = "HIT"
                headers["X-Cache-Key"] = cache_key[:16] + "..."
                
                return Response(
                    content=data["body"],
                    status_code=data["status_code"],
                    headers=headers,
                    media_type="application/json"
                )
        except Exception as e:
            # Cache error shouldn't break the request
            pass
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses only
        if response.status_code == 200:
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                cache_data = {
                    "body": body.decode(),
                    "status_code": response.status_code,
                    "headers": {k: v for k, v in response.headers.items() 
                               if k.lower() not in ["content-length", "transfer-encoding"]}
                }
                
                # Cache for 5 minutes
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(cache_data)
                )
                
                # Return with cache miss header
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers={**response.headers, "X-Cache": "MISS"},
                    media_type=response.media_type
                )
            except Exception as e:
                # Cache write error shouldn't break the request
                pass
        
        return response
    
    async def _generate_cache_key(self, request: Request) -> str:
        """Generate unique cache key from request."""
        # Read body
        body = await request.body()
        
        key_parts = [
            request.method,
            str(request.url.path),
            body.decode() if body else ""
        ]
        key_string = "|".join(key_parts)
        
        # Reset body for downstream middleware
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive
        
        return f"ape:cache:{hashlib.sha256(key_string.encode()).hexdigest()[:32]}"


class CacheStats:
    """Cache statistics tracker."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            info = await self.redis.info("stats")
            keys = await self.redis.keys("ape:cache:*")
            
            return {
                "cache_keys_count": len(keys),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
                "memory_used_human": info.get("used_memory_human", "unknown")
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_hit_rate(self, info: dict) -> float:
        """Calculate cache hit rate."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round(hits / total * 100, 2)
