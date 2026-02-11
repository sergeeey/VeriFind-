"""
Performance Profiling Middleware for APE 2026
Week 10 - Performance Optimization

Tracks request timing and identifies slow endpoints.
"""

import time
import logging
from typing import Optional
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ProfilingMiddleware(BaseHTTPMiddleware):
    """Track request performance with metrics."""
    
    def __init__(self, app, slow_threshold: float = 2.0, max_history: int = 1000):
        super().__init__(app)
        self.slow_threshold = slow_threshold  # Log requests slower than this (seconds)
        self.max_history = max_history
        
        # Performance history for metrics
        self.request_times = defaultdict(lambda: deque(maxlen=max_history))
        self.error_count = 0
        self.total_requests = 0
        
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        self.total_requests += 1
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.perf_counter() - start_time
            
            # Store for metrics
            endpoint = f"{request.method}:{request.url.path}"
            self.request_times[endpoint].append(duration)
            
            # Log slow requests
            if duration > self.slow_threshold:
                logger.warning(
                    f"🐌 Slow request: {request.method} {request.url.path} "
                    f"took {duration:.3f}s (threshold: {self.slow_threshold}s)"
                )
            
            # Add timing headers
            response.headers["X-Process-Time"] = f"{duration:.3f}"
            response.headers["X-Request-Count"] = str(self.total_requests)
            
            return response
            
        except Exception as e:
            self.error_count += 1
            duration = time.perf_counter() - start_time
            logger.error(
                f"❌ Request failed: {request.method} {request.url.path} "
                f"after {duration:.3f}s - {str(e)}"
            )
            raise
    
    def get_stats(self) -> dict:
        """Get performance statistics."""
        stats = {
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.total_requests, 1) * 100, 2),
            "endpoints": {}
        }
        
        for endpoint, times in self.request_times.items():
            if times:
                sorted_times = sorted(times)
                stats["endpoints"][endpoint] = {
                    "count": len(times),
                    "p50": round(sorted_times[len(times) // 2], 3),
                    "p95": round(sorted_times[int(len(times) * 0.95)], 3) if len(times) >= 20 else None,
                    "p99": round(sorted_times[int(len(times) * 0.99)], 3) if len(times) >= 100 else None,
                    "min": round(min(times), 3),
                    "max": round(max(times), 3),
                    "avg": round(sum(times) / len(times), 3)
                }
        
        return stats


class MemoryProfiler:
    """Track memory usage (optional, requires psutil)."""
    
    def __init__(self):
        self.has_psutil = False
        try:
            import psutil
            self.has_psutil = True
            self.process = psutil.Process()
        except ImportError:
            pass
    
    def get_memory_stats(self) -> Optional[dict]:
        """Get current memory usage."""
        if not self.has_psutil:
            return None
        
        import psutil
        
        mem_info = self.process.memory_info()
        system_mem = psutil.virtual_memory()
        
        return {
            "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
            "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
            "percent": self.process.memory_percent(),
            "system_percent": system_mem.percent,
            "system_available_mb": round(system_mem.available / 1024 / 1024, 2)
        }
