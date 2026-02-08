"""
API Configuration
Week 9 Day 1 (Security Hardening)

Environment-based configuration for FastAPI application.
Enhanced with production secrets validation and security settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator
from typing import Dict, List, Optional, Any
import os


class APISettings(BaseSettings):
    """API configuration settings."""

    # API Info
    app_name: str = "APE 2026 API"
    app_version: str = "1.0.0"
    app_description: str = "Autonomous Precision Engine for Financial Analysis"

    # Server
    host: str = Field("0.0.0.0", env="API_HOST")
    port: int = Field(8000, env="API_PORT")
    reload: bool = Field(False, env="API_RELOAD")
    workers: int = Field(1, env="API_WORKERS")

    # CORS (for env var, use comma-separated: "http://localhost:3000,http://localhost:8000")
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Authentication & Security
    api_keys: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "dev_key_12345": {"name": "Development", "rate_limit": 100},
            "test_key_99999": {"name": "Testing", "rate_limit": 1000}
        }
    )
    secret_key: str = Field("dev_secret_key_change_in_production", env="SECRET_KEY")
    environment: str = Field("development", env="ENVIRONMENT")

    # Rate Limiting
    rate_limit_window_hours: int = Field(1, env="RATE_LIMIT_WINDOW_HOURS")
    default_rate_limit: int = Field(100, env="DEFAULT_RATE_LIMIT")

    # Database URLs (optional, fallback to env vars)
    timescaledb_url: str = Field(
        "postgresql://ape_user:ape_pass@localhost:5433/ape_db",
        env="TIMESCALEDB_URL"
    )
    neo4j_uri: str = Field("bolt://localhost:7688", env="NEO4J_URI")
    neo4j_user: str = Field("neo4j", env="NEO4J_USER")
    neo4j_password: str = Field("ape_neo4j_pass", env="NEO4J_PASSWORD")
    redis_url: str = Field("redis://localhost:6380/0", env="REDIS_URL")

    # Query Execution
    query_timeout_seconds: int = Field(120, env="QUERY_TIMEOUT_SECONDS")
    max_concurrent_queries: int = Field(10, env="MAX_CONCURRENT_QUERIES")

    # External APIs (Optional - for AI models and market data)
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    alpha_vantage_api_key: Optional[str] = Field(None, env="ALPHA_VANTAGE_API_KEY")
    polygon_api_key: Optional[str] = Field(None, env="POLYGON_API_KEY")

    # Sandbox Execution (VEE node)
    sandbox_timeout_seconds: int = Field(30, env="SANDBOX_TIMEOUT_SECONDS")
    sandbox_max_memory_mb: int = Field(512, env="SANDBOX_MAX_MEMORY_MB")
    sandbox_enable_network: bool = Field(False, env="SANDBOX_ENABLE_NETWORK")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Async Execution
    use_background_tasks: bool = Field(True, env="USE_BACKGROUND_TASKS")
    task_queue_max_size: int = Field(1000, env="TASK_QUEUE_MAX_SIZE")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Ensure environment is valid."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @model_validator(mode='after')
    def validate_production_secrets(self):
        """Validate production secrets after all fields are set."""
        if self.environment == "production":
            # Check SECRET_KEY
            if self.secret_key == "dev_secret_key_change_in_production":
                raise ValueError(
                    "SECRET_KEY must be changed in production. "
                    "Set environment variable SECRET_KEY to a secure random value."
                )
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")

            # Check database credentials
            if self.timescaledb_url == "postgresql://ape_user:ape_pass@localhost:5433/ape_db":
                raise ValueError(
                    "timescaledb_url uses default credentials. "
                    "Set environment variable TIMESCALEDB_URL with production credentials."
                )
            if self.neo4j_password == "ape_neo4j_pass":
                raise ValueError(
                    "neo4j_password uses default credentials. "
                    "Set environment variable NEO4J_PASSWORD with production credentials."
                )

        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file


# Singleton settings instance
_settings = None


def get_settings() -> APISettings:
    """Get settings singleton."""
    global _settings
    if _settings is None:
        _settings = APISettings()
    return _settings


# Production API keys (load from environment)
def load_production_api_keys() -> Dict[str, Dict[str, any]]:
    """
    Load production API keys from environment.

    Expected format: API_KEY_<NAME>=<key>:<rate_limit>
    Example: API_KEY_PROD=prod_key_67890:1000
    """
    keys = {}
    for key, value in os.environ.items():
        if key.startswith("API_KEY_"):
            name = key.replace("API_KEY_", "")
            try:
                api_key, rate_limit = value.split(":")
                keys[api_key] = {
                    "name": name,
                    "rate_limit": int(rate_limit)
                }
            except ValueError:
                print(f"Warning: Invalid API key format for {key}: {value}")
                continue

    return keys
