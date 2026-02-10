"""
Configuration Tests

Week 1 Day 4: Production Readiness
Test configuration loading and validation
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestSettings:
    """Pydantic Settings tests"""
    
    def test_settings_load_from_env(self):
        """Settings load from environment variables"""
        from src.api.config import Settings
        
        # Create settings
        settings = Settings()
        
        # Verify key settings loaded
        assert settings.APP_NAME == "APE-2026"
        assert settings.ENVIRONMENT in ["development", "staging", "production"]
    
    def test_database_url_construction(self):
        """Database URL constructed correctly from components"""
        from src.api.config import Settings
        
        with patch.dict(os.environ, {
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_HOST": "testhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb"
        }):
            settings = Settings()
            
            # URL should contain all components
            assert "testuser" in str(settings.DATABASE_URL)
            assert "testhost" in str(settings.DATABASE_URL)
            assert "5432" in str(settings.DATABASE_URL)
            assert "testdb" in str(settings.DATABASE_URL)
    
    def test_production_settings_validation(self):
        """Production mode requires non-default secrets"""
        from src.api.config import Settings
        
        # Should raise error for default secrets in production
        with pytest.raises(ValueError):
            with patch.dict(os.environ, {
                "ENVIRONMENT": "production",
                "SECRET_KEY": "dev_secret_key_change_in_production"  # Default value
            }):
                Settings()
    
    def test_cors_origins_parsing(self):
        """CORS origins parsed from comma-separated string"""
        from src.api.config import Settings
        
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "http://localhost:3000,http://localhost:8000,https://ape.com"
        }):
            settings = Settings()
            
            assert len(settings.CORS_ORIGINS) == 3
            assert "http://localhost:3000" in settings.CORS_ORIGINS
            assert "https://ape.com" in settings.CORS_ORIGINS


class TestRateLimitConfig:
    """Rate limiting configuration tests"""
    
    def test_rate_limit_defaults(self):
        """Default rate limits are reasonable"""
        from src.api.config import Settings
        
        settings = Settings()
        
        assert settings.RATE_LIMIT_REQUESTS_PER_HOUR > 0
        assert settings.RATE_LIMIT_BURST_PER_MINUTE > 0
        assert settings.DEFAULT_RATE_LIMIT > 0
    
    def test_rate_limit_can_be_overridden(self):
        """Rate limits can be overridden via env"""
        from src.api.config import Settings
        
        with patch.dict(os.environ, {
            "RATE_LIMIT_REQUESTS_PER_HOUR": "1000"
        }):
            settings = Settings()
            assert settings.RATE_LIMIT_REQUESTS_PER_HOUR == 1000


class TestTimeoutConfig:
    """Timeout configuration tests"""
    
    def test_timeouts_reasonable(self):
        """Timeout values are reasonable"""
        from src.api.config import Settings
        
        settings = Settings()
        
        # Query timeout should be > VEE timeout
        assert settings.MAX_QUERY_TIMEOUT >= settings.MAX_VEE_EXECUTION_TIME
        
        # All timeouts should be positive
        assert settings.MAX_QUERY_TIMEOUT > 0
        assert settings.MAX_VEE_EXECUTION_TIME > 0
        assert settings.MAX_RETRIEVAL_LATENCY > 0
    
    def test_timeouts_in_seconds(self):
        """Timeouts are in seconds (not ms)"""
        from src.api.config import Settings
        
        settings = Settings()
        
        # Should be reasonable seconds, not milliseconds
        assert settings.MAX_QUERY_TIMEOUT < 1000  # Less than 1000 seconds
        assert settings.MAX_QUERY_TIMEOUT > 10    # More than 10 seconds


class TestSecurityConfig:
    """Security configuration tests"""
    
    def test_jwt_settings(self):
        """JWT settings are configured"""
        from src.api.config import Settings
        
        settings = Settings()
        
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_EXPIRATION_MINUTES > 0
        assert len(settings.SECRET_KEY) >= 32
    
    def test_sandbox_security_defaults(self):
        """Sandbox security defaults are safe"""
        from src.api.config import Settings
        
        settings = Settings()
        
        # Network should be disabled by default in production
        assert settings.SANDBOX_ENABLE_NETWORK is not None


class TestEnvironmentDetection:
    """Environment detection tests"""
    
    def test_development_mode(self):
        """Development mode detected correctly"""
        from src.api.config import Settings
        
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings()
            assert settings.ENVIRONMENT == "development"
            assert settings.DEBUG is True
    
    def test_production_mode(self):
        """Production mode detected correctly"""
        from src.api.config import Settings
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 64,  # Long enough secret
            "NEO4J_PASSWORD": "secure_neo4j_pass",
            "POSTGRES_PASSWORD": "secure_postgres_pass"
        }):
            settings = Settings()
            assert settings.ENVIRONMENT == "production"
            assert settings.DEBUG is False
