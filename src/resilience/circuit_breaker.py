"""
Circuit Breaker Pattern for API Resilience

Week 2 Day 8: Production Readiness
Prevents cascade failures when external APIs are down
"""

import time
import logging
import asyncio
from enum import Enum
from typing import Callable, Optional, Any, Dict
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes to close from half-open
    timeout: float = 60.0               # Seconds before attempting reset
    half_open_max_calls: int = 3        # Max calls in half-open state
    expected_exception: type = Exception  # Exception type to count as failure


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker '{name}' is open. Retry after {retry_after:.1f}s")


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, requests rejected immediately
    - HALF_OPEN: Testing if service recovered
    
    Usage:
        breaker = CircuitBreaker("deepseek", failure_threshold=5)
        
        @breaker
        async def call_deepseek(prompt):
            return await deepseek_client.generate(prompt)
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        self.total_calls += 1
        
        # Check if we should attempt state transition
        await self._update_state()
        
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpen(
                self.name,
                self._time_until_retry()
            )
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpen(
                    self.name,
                    self.config.timeout
                )
            self.half_open_calls += 1
        
        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
            
        except self.config.expected_exception as e:
            await self._on_failure()
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator support"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        
        wrapper._circuit_breaker = self
        return wrapper
    
    async def _update_state(self):
        """Update circuit state based on time and failures"""
        if self.state == CircuitState.OPEN:
            if self._time_until_retry() <= 0:
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.success_count = 0
    
    async def _on_success(self):
        """Handle successful call"""
        self.total_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.half_open_calls = 0
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call"""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' failed in HALF_OPEN, transitioning to OPEN")
            self.state = CircuitState.OPEN
            
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker '{self.name}' exceeded failure threshold "
                    f"({self.failure_count}/{self.config.failure_threshold}), transitioning to OPEN"
                )
                self.state = CircuitState.OPEN
    
    def _time_until_retry(self) -> float:
        """Calculate time until next retry attempt"""
        if self.state != CircuitState.OPEN:
            return 0
        
        if self.last_failure_time is None:
            return 0
        
        elapsed = time.time() - self.last_failure_time
        remaining = self.config.timeout - elapsed
        return max(0, remaining)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "failure_rate": self.total_failures / max(self.total_calls, 1),
            "time_until_retry": self._time_until_retry(),
        }


class LLMProviderChain:
    """Chain of LLM providers with circuit breakers and fallback"""
    
    def __init__(self, providers: list):
        self.providers = []
        
        for name, client, config in providers:
            breaker = CircuitBreaker(name, config)
            self.providers.append({
                "name": name,
                "client": client,
                "breaker": breaker
            })
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using available provider"""
        last_error = None
        
        for provider in self.providers:
            name = provider["name"]
            client = provider["client"]
            breaker = provider["breaker"]
            
            try:
                result = await breaker.call(
                    client.generate,
                    prompt=prompt,
                    **kwargs
                )
                return result
                
            except CircuitBreakerOpen:
                continue
                
            except Exception as e:
                last_error = e
                continue
        
        raise Exception(f"All LLM providers failed. Last error: {last_error}")


# Global circuit breakers
deepseek_breaker = CircuitBreaker("deepseek", CircuitBreakerConfig(failure_threshold=5))
anthropic_breaker = CircuitBreaker("anthropic", CircuitBreakerConfig(failure_threshold=3))
