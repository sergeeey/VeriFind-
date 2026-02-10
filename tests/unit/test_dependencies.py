"""
Dependency Injection Tests

Week 1 Day 4: Production Readiness
Test FastAPI dependencies
"""

import pytest
from unittest.mock import patch, MagicMock


class TestDependencyInjection:
    """DI container tests"""
    
    def test_get_orchestrator_singleton(self):
        """Orchestrator is a singleton"""
        from src.api.dependencies import get_orchestrator
        
        # Get orchestrator twice
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        
        # Should be same instance
        assert orch1 is orch2
    
    def test_get_timescale_store_singleton(self):
        """TimescaleDB store is a singleton"""
        from src.api.dependencies import get_timescale_store
        
        store1 = get_timescale_store()
        store2 = get_timescale_store()
        
        assert store1 is store2
    
    def test_get_neo4j_client_singleton(self):
        """Neo4j client is a singleton"""
        from src.api.dependencies import get_neo4j_client
        
        client1 = get_neo4j_client()
        client2 = get_neo4j_client()
        
        assert client1 is client2


class TestDatabaseDependency:
    """Database dependency tests"""
    
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """get_db yields a database session"""
        from src.api.dependencies import get_db
        
        # Mock the database
        with patch("src.api.dependencies.async_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__aenter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = MagicMock(return_value=None)
            
            # Get the dependency
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            assert db is not None
    
    def test_db_dependency_injection(self):
        """DB can be injected into routes"""
        from fastapi import Depends
        from src.api.dependencies import get_db
        
        # Test that get_db is callable
        assert callable(get_db)


class TestRateLimiter:
    """Rate limiter dependency tests"""
    
    def test_rate_limiter_exists(self):
        """Rate limiter dependency exists"""
        from src.api.dependencies import get_rate_limiter
        
        limiter = get_rate_limiter()
        assert limiter is not None
    
    def test_rate_limiter_configuration(self):
        """Rate limiter has correct configuration"""
        from src.api.dependencies import get_rate_limiter
        
        limiter = get_rate_limiter()
        
        # Should have limits configured
        assert hasattr(limiter, 'default_limits') or hasattr(limiter, 'limits')


class TestAPIKeyAuth:
    """API key authentication tests"""
    
    def test_verify_api_key_exists(self):
        """API key verification function exists"""
        from src.api.dependencies import verify_api_key
        
        assert callable(verify_api_key)
    
    def test_verify_api_key_valid(self):
        """Valid API key passes verification"""
        from src.api.dependencies import verify_api_key
        
        # Mock settings
        with patch("src.api.dependencies.settings") as mock_settings:
            mock_settings.API_KEY = "valid_key_123"
            
            # Should not raise for valid key
            try:
                result = verify_api_key("valid_key_123")
                assert result is not None
            except Exception as e:
                pytest.fail(f"Valid key should not raise: {e}")
    
    def test_verify_api_key_invalid(self):
        """Invalid API key fails verification"""
        from src.api.dependencies import verify_api_key
        from fastapi import HTTPException
        
        with patch("src.api.dependencies.settings") as mock_settings:
            mock_settings.API_KEY = "valid_key_123"
            
            # Should raise for invalid key
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key("invalid_key")
            
            assert exc_info.value.status_code == 401


class TestOrchestratorDI:
    """Orchestrator dependency injection tests"""
    
    def test_orchestrator_has_required_methods(self):
        """Orchestrator has required methods"""
        from src.api.dependencies import get_orchestrator
        
        orchestrator = get_orchestrator()
        
        # Should have run method
        assert hasattr(orchestrator, 'run')
        assert callable(getattr(orchestrator, 'run'))
    
    def test_orchestrator_initialized_once(self):
        """Orchestrator initialized only once"""
        from src.api.dependencies import get_orchestrator
        
        with patch("src.api.dependencies.LangGraphOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            
            # Get multiple times
            _ = get_orchestrator()
            _ = get_orchestrator()
            _ = get_orchestrator()
            
            # Should only initialize once
            assert mock_orch.call_count == 1


class TestDependencyCleanup:
    """Test cleanup of dependencies"""
    
    def test_singletons_not_recreated(self):
        """Singletons persist across multiple requests"""
        from src.api.dependencies import (
            get_orchestrator,
            get_timescale_store,
            get_neo4j_client
        )
        
        # Get multiple times
        orch_ids = [id(get_orchestrator()) for _ in range(5)]
        store_ids = [id(get_timescale_store()) for _ in range(5)]
        client_ids = [id(get_neo4j_client()) for _ in range(5)]
        
        # All should be same instance
        assert len(set(orch_ids)) == 1
        assert len(set(store_ids)) == 1
        assert len(set(client_ids)) == 1
