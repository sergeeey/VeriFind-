"""
API Configuration
Week 6 Day 4

Environment-based configuration for FastAPI application.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, List
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
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Authentication
    api_keys: Dict[str, Dict[str, any]] = Field(
        default_factory=lambda: {
            "dev_key_12345": {"name": "Development", "rate_limit": 100},
            "test_key_99999": {"name": "Testing", "rate_limit": 1000}
        }
    )

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

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Async Execution
    use_background_tasks: bool = Field(True, env="USE_BACKGROUND_TASKS")
    task_queue_max_size: int = Field(1000, env="TASK_QUEUE_MAX_SIZE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


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
