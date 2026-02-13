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
        load_dotenv(env_path, override=True)
        print(f"\n✅ Loaded environment variables from {env_path}")
    else:
        print(f"\n⚠️  No .env file found at {env_path}")

    # Ensure Docker SDK uses Windows named pipe
    os.environ["DOCKER_HOST"] = "npipe:////./pipe/docker_engine"

    # Register custom markers
    config.addinivalue_line(
        "markers", "realapi: mark test as requiring real API keys (skipped if keys not available)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (takes >30 seconds)"
    )


# Docker availability check for integration tests
_docker_available_cache = None

def _docker_available():
    global _docker_available_cache
    if _docker_available_cache is not None:
        return _docker_available_cache
    try:
        import docker
        client = docker.from_env()
        client.version()
        _docker_available_cache = True
    except Exception:
        _docker_available_cache = False
    return _docker_available_cache


def pytest_ignore_collect(path, config):
    # Skip Docker-dependent integration tests if Docker is not available
    if not _docker_available():
        docker_tests = {
            "test_e2e_pipeline_with_persistence.py",
            "test_golden_set_integration.py",
            "test_golden_set_quick.py",
            "test_orchestrator_real_llm.py",
            "test_plan_vee_gate_pipeline.py"
        }
        if path.basename in docker_tests or "golden_set" in path.basename:
            return True
    return False
