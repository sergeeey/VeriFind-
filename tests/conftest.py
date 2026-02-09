"""Pytest configuration and fixtures.

Automatically loads .env file for all tests.
"""

import pytest
from dotenv import load_dotenv
import os


def pytest_configure(config):
    """Load .env file and register custom markers."""
    # Load .env from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"\n✅ Loaded environment variables from {env_path}")
    else:
        print(f"\n⚠️  No .env file found at {env_path}")

    # Register custom markers
    config.addinivalue_line(
        "markers", "realapi: mark test as requiring real API keys (skipped if keys not available)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (takes >30 seconds)"
    )
