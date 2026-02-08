"""
Unit Tests for FastAPI Endpoints
Week 6 Day 4

Tests for REST API endpoints, authentication, rate limiting.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

# Mock the dependencies before importing the app
import sys
sys.modules['src.orchestration.langgraph_orchestrator'] = MagicMock()
sys.modules['src.storage.timescale_store'] = MagicMock()
sys.modules['src.graph.neo4j_client'] = MagicMock()
sys.modules['src.vectorstore.chromadb_client'] = MagicMock()

from src.api.main import app
from src.api.config import get_settings
from src.api.dependencies import _rate_limit_store, verify_api_key, check_rate_limit


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Valid API key for testing."""
    return "dev_key_12345"


@pytest.fixture
def invalid_api_key():
    """Invalid API key for testing."""
    return "invalid_key_00000"


@pytest.fixture(autouse=True)
def reset_rate_limit_store():
    """Reset rate limit store before each test."""
    global _rate_limit_store
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


# ============================================================================
# Health Check Tests
# ============================================================================

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert data["version"] == "1.0.0"
    assert "components" in data
    assert data["components"]["api"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint redirects to docs."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "message" in data
    assert data["message"] == "APE 2026 API"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


# ============================================================================
# Authentication Tests
# ============================================================================

def test_query_without_api_key(client):
    """Test query submission without API key."""
    response = client.post(
        "/query",
        json={"query": "Calculate Sharpe ratio of SPY for 2023"}
    )

    assert response.status_code == 401
    data = response.json()
    assert "Missing API key" in data["error"]


def test_query_with_invalid_api_key(client, invalid_api_key):
    """Test query submission with invalid API key."""
    response = client.post(
        "/query",
        json={"query": "Calculate Sharpe ratio of SPY for 2023"},
        headers={"X-API-Key": invalid_api_key}
    )

    assert response.status_code == 401
    data = response.json()
    assert "Invalid API key" in data["error"]


def test_query_with_valid_api_key(client, valid_api_key):
    """Test query submission with valid API key."""
    response = client.post(
        "/query",
        json={"query": "Calculate Sharpe ratio of SPY for 2023"},
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 202  # Accepted
    data = response.json()

    assert "query_id" in data
    assert data["status"] == "accepted"
    assert "estimated_completion" in data


# ============================================================================
# Query Validation Tests
# ============================================================================

def test_query_too_short(client, valid_api_key):
    """Test query validation: too short."""
    response = client.post(
        "/query",
        json={"query": "SPY"},
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data


def test_query_too_long(client, valid_api_key):
    """Test query validation: too long."""
    long_query = "Calculate " + ("very " * 100) + "long query"

    response = client.post(
        "/query",
        json={"query": long_query},
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 422  # Validation error


def test_query_empty(client, valid_api_key):
    """Test query validation: empty string."""
    response = client.post(
        "/query",
        json={"query": "   "},
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 422  # Validation error


def test_query_with_priority(client, valid_api_key):
    """Test query with priority levels."""
    for priority in ["low", "normal", "high"]:
        response = client.post(
            "/query",
            json={
                "query": "Calculate Sharpe ratio of SPY",
                "priority": priority
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"


def test_query_with_invalid_priority(client, valid_api_key):
    """Test query with invalid priority."""
    response = client.post(
        "/query",
        json={
            "query": "Calculate Sharpe ratio of SPY",
            "priority": "urgent"  # Invalid
        },
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 422  # Validation error


def test_query_with_metadata(client, valid_api_key):
    """Test query with metadata."""
    response = client.post(
        "/query",
        json={
            "query": "Calculate Sharpe ratio of SPY",
            "metadata": {"user_id": "test_user", "source": "web"}
        },
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"


# ============================================================================
# Rate Limiting Tests
# ============================================================================

def test_rate_limit_exceeded(client, valid_api_key):
    """Test rate limit enforcement."""
    settings = get_settings()
    limit = settings.api_keys[valid_api_key]["rate_limit"]

    # Make requests up to limit
    for i in range(limit):
        response = client.post(
            "/query",
            json={"query": f"Test query {i}"},
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 202

    # Next request should be rate limited
    response = client.post(
        "/query",
        json={"query": "Should be rate limited"},
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 429  # Too Many Requests
    data = response.json()
    assert "Rate limit exceeded" in data["error"]


def test_rate_limit_headers(client, valid_api_key):
    """Test rate limit response headers."""
    settings = get_settings()
    limit = settings.api_keys[valid_api_key]["rate_limit"]

    # Exhaust rate limit
    for i in range(limit):
        client.post(
            "/query",
            json={"query": f"Test {i}"},
            headers={"X-API-Key": valid_api_key}
        )

    # Check rate limit response headers
    response = client.post(
        "/query",
        json={"query": "Rate limited"},
        headers={"X-API-Key": valid_api_key}
    )

    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    assert response.headers["X-RateLimit-Remaining"] == "0"


# ============================================================================
# Status Endpoint Tests
# ============================================================================

def test_get_status_without_api_key(client):
    """Test status endpoint without API key."""
    query_id = str(uuid4())
    response = client.get(f"/status/{query_id}")

    assert response.status_code == 401


def test_get_status_with_valid_api_key(client, valid_api_key):
    """Test status endpoint with valid API key."""
    query_id = str(uuid4())
    response = client.get(
        f"/status/{query_id}",
        headers={"X-API-Key": valid_api_key}
    )

    # Should return mock status (for now)
    assert response.status_code == 200
    data = response.json()

    assert data["query_id"] == query_id
    assert "status" in data
    assert "progress" in data
    assert 0.0 <= data["progress"] <= 1.0


# ============================================================================
# Episodes Endpoint Tests
# ============================================================================

def test_get_episode_without_api_key(client):
    """Test episode endpoint without API key."""
    episode_id = str(uuid4())
    response = client.get(f"/episodes/{episode_id}")

    assert response.status_code == 401


def test_get_episode_with_valid_api_key(client, valid_api_key):
    """Test episode endpoint with valid API key."""
    episode_id = str(uuid4())
    response = client.get(
        f"/episodes/{episode_id}",
        headers={"X-API-Key": valid_api_key}
    )

    # Should return mock episode (for now)
    assert response.status_code == 200
    data = response.json()

    assert data["episode_id"] == episode_id
    assert "query_text" in data
    assert "verified_facts" in data
    assert isinstance(data["verified_facts"], list)


# ============================================================================
# Facts Endpoint Tests
# ============================================================================

def test_list_facts_without_api_key(client):
    """Test facts list endpoint without API key."""
    response = client.get("/facts")

    assert response.status_code == 401


def test_list_facts_with_valid_api_key(client, valid_api_key):
    """Test facts list endpoint with valid API key."""
    response = client.get(
        "/facts",
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)


def test_list_facts_with_pagination(client, valid_api_key):
    """Test facts list with pagination parameters."""
    response = client.get(
        "/facts?limit=10&offset=5",
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_facts_with_query_filter(client, valid_api_key):
    """Test facts list filtered by query_id."""
    query_id = str(uuid4())
    response = client.get(
        f"/facts?query_id={query_id}",
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_invalid_endpoint(client, valid_api_key):
    """Test request to non-existent endpoint."""
    response = client.get(
        "/nonexistent",
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 404


def test_method_not_allowed(client, valid_api_key):
    """Test wrong HTTP method."""
    response = client.get(  # Should be POST
        "/query",
        headers={"X-API-Key": valid_api_key}
    )

    assert response.status_code == 405  # Method Not Allowed


# ============================================================================
# Integration Tests (require mocked dependencies)
# ============================================================================

@pytest.mark.integration
def test_full_query_workflow(client, valid_api_key):
    """Test complete query submission and status check workflow."""

    # 1. Submit query
    submit_response = client.post(
        "/query",
        json={
            "query": "Calculate Sharpe ratio of SPY for 2023",
            "priority": "high"
        },
        headers={"X-API-Key": valid_api_key}
    )

    assert submit_response.status_code == 202
    submit_data = submit_response.json()
    query_id = submit_data["query_id"]

    # 2. Check status
    status_response = client.get(
        f"/status/{query_id}",
        headers={"X-API-Key": valid_api_key}
    )

    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["query_id"] == query_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
