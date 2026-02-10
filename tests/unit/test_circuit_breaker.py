"""
Circuit Breaker Tests

Week 2 Day 8: Production Readiness
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


class TestCircuitBreaker:
    """Circuit breaker tests"""
    
    @pytest.mark.asyncio
    async def test_closed_state_allows_calls(self):
        """Closed state allows calls through"""
        from src.resilience.circuit_breaker import CircuitBreaker, CircuitState
        
        breaker = CircuitBreaker("test", MagicMock(failure_threshold=3))
        
        # Mock function that succeeds
        mock_func = AsyncMock(return_value="success")
        
        result = await breaker.call(mock_func, "arg1")
        
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.total_calls == 1
    
    @pytest.mark.asyncio
    async def test_opens_after_failures(self):
        """Circuit opens after threshold failures"""
        from src.resilience.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpen
        
        breaker = CircuitBreaker("test", MagicMock(failure_threshold=3))
        
        # Mock function that fails
        mock_func = AsyncMock(side_effect=Exception("fail"))
        
        # Call 3 times (threshold)
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Circuit should be open
        assert breaker.state == CircuitState.OPEN
        
        # Next call should raise CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen):
            await breaker.call(mock_func)
    
    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        """Circuit transitions to half-open after timeout"""
        from src.resilience.circuit_breaker import CircuitBreaker, CircuitState
        
        config = MagicMock(failure_threshold=3, timeout=0.001)  # Very short timeout
        breaker = CircuitBreaker("test", config)
        
        # Open the circuit
        mock_func = AsyncMock(side_effect=Exception("fail"))
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.01)
        
        # Update state
        await breaker._update_state()
        
        # Should be half-open
        assert breaker.state == CircuitState.HALF_OPEN


class TestLLMProviderChain:
    """LLM provider chain tests"""
    
    @pytest.mark.asyncio
    async def test_fallback_to_next_provider(self):
        """Falls back to next provider when primary fails"""
        from src.resilience.circuit_breaker import LLMProviderChain, CircuitBreakerConfig
        
        # Primary fails
        primary = AsyncMock()
        primary.generate = AsyncMock(side_effect=Exception("fail"))
        
        # Secondary succeeds
        secondary = AsyncMock()
        secondary.generate = AsyncMock(return_value="success")
        
        chain = LLMProviderChain([
            ("primary", primary, CircuitBreakerConfig(failure_threshold=1)),
            ("secondary", secondary, CircuitBreakerConfig()),
        ])
        
        result = await chain.generate("prompt")
        
        assert result == "success"
        secondary.generate.assert_called_once()
