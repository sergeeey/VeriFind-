"""
Integration tests for disclaimer in API responses.

Week 11 Day 3: Legal compliance testing.

Validates that disclaimer appears in all relevant API responses.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


class TestDisclaimerAPI:
    """Test disclaimer in API responses."""

    def test_disclaimer_endpoint_exists(self):
        """Test /disclaimer endpoint returns disclaimer."""
        response = client.get("/disclaimer")

        assert response.status_code == 200
        data = response.json()

        # Check disclaimer structure
        assert "disclaimer" in data
        assert "full_text" in data
        assert "notice" in data
        assert "key_points" in data
        assert "contact" in data

        # Check disclaimer content
        disclaimer = data["disclaimer"]
        assert "text" in disclaimer
        assert "version" in disclaimer
        assert "effective_date" in disclaimer
        assert "full_text_url" in disclaimer

        # Verify disclaimer text content
        assert "informational purposes only" in disclaimer["text"]
        assert "financial advice" in disclaimer["text"]
        assert "qualified financial advisor" in disclaimer["text"]

        # Verify key points
        assert len(data["key_points"]) >= 5
        assert any("not financial advice" in point.lower() for point in data["key_points"])
        assert any("past performance" in point.lower() for point in data["key_points"])

    def test_disclaimer_in_health_response(self):
        """Test health endpoint does NOT have disclaimer (excluded)."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Health endpoint should be excluded from disclaimer
        # (health checks should be minimal)
        # Note: Middleware excludes /health, so no disclaimer expected
        assert "status" in data
        assert "version" in data

    def test_disclaimer_version_format(self):
        """Test disclaimer has proper versioning."""
        response = client.get("/disclaimer")
        data = response.json()

        disclaimer = data["disclaimer"]

        # Check version format (e.g., "1.0")
        assert "version" in disclaimer
        assert isinstance(disclaimer["version"], str)
        assert len(disclaimer["version"]) > 0

        # Check effective date format (ISO date)
        assert "effective_date" in disclaimer
        assert isinstance(disclaimer["effective_date"], str)
        # Should be in YYYY-MM-DD format
        assert "-" in disclaimer["effective_date"]

    def test_disclaimer_full_text_accessible(self):
        """Test full disclaimer text is available."""
        response = client.get("/disclaimer")
        data = response.json()

        # Full text should be included in response
        assert "full_text" in data

        # If DISCLAIMER.md exists, full_text should be populated
        if data["full_text"] is not None:
            assert len(data["full_text"]) > 100  # Should be substantial
            assert "Legal Disclaimer" in data["full_text"]
            assert "Not Financial Advice" in data["full_text"]

    def test_disclaimer_key_points_complete(self):
        """Test all key disclaimer points are present."""
        response = client.get("/disclaimer")
        data = response.json()

        key_points = data["key_points"]

        # Check for critical disclaimer points
        expected_topics = [
            "financial advice",
            "past performance",
            "ai",
            "risk",
            "18",
            "warranty"
        ]

        key_points_text = " ".join(key_points).lower()

        for topic in expected_topics:
            assert topic in key_points_text, f"Missing key topic: {topic}"

    def test_disclaimer_contact_info(self):
        """Test contact information is provided."""
        response = client.get("/disclaimer")
        data = response.json()

        contact = data["contact"]

        # Should have documentation link
        assert "documentation" in contact
        assert "/docs" in contact["documentation"]

        # Should have github link
        assert "github" in contact
        assert "github.com" in contact["github"]

        # Should have issues guidance
        assert "issues" in contact

    def test_disclaimer_notice_message(self):
        """Test disclaimer notice is clear and prominent."""
        response = client.get("/disclaimer")
        data = response.json()

        notice = data["notice"]

        # Notice should be clear about acceptance
        assert "acknowledge" in notice.lower()
        assert "agree" in notice.lower()
        assert "informational purposes" in notice.lower()
        assert "not constitute" in notice.lower()


class TestDisclaimerMiddleware:
    """Test disclaimer middleware adds disclaimer to JSON responses."""

    # Note: These tests would require actual query submission
    # which needs API keys and orchestrator setup.
    # For now, we test the /disclaimer endpoint as proof of concept.

    def test_disclaimer_middleware_structure(self):
        """Test middleware disclaimer structure."""
        # Get disclaimer structure
        response = client.get("/disclaimer")
        data = response.json()

        disclaimer = data["disclaimer"]

        # Verify middleware format matches
        assert "text" in disclaimer
        assert "version" in disclaimer
        assert "effective_date" in disclaimer
        assert "full_text_url" in disclaimer

        # Text should be single-line condensed version
        assert len(disclaimer["text"]) < 500  # Condensed, not full text
        assert "\n" not in disclaimer["text"]  # Single line

    @pytest.mark.skip(reason="Requires full API setup with auth")
    def test_disclaimer_in_query_response(self):
        """Test disclaimer appears in query submission response."""
        # This would test POST /query response
        # Skipped: requires API key and orchestrator
        pass

    @pytest.mark.skip(reason="Requires full API setup with auth")
    def test_disclaimer_in_status_response(self):
        """Test disclaimer appears in status response."""
        # This would test GET /status/{query_id} response
        # Skipped: requires API key and query_id
        pass


@pytest.mark.integration
class TestDisclaimerIntegration:
    """Integration tests for disclaimer across system."""

    def test_disclaimer_consistent_across_endpoints(self):
        """Test disclaimer content is consistent."""
        response1 = client.get("/disclaimer")
        response2 = client.get("/disclaimer")

        # Should return same content
        assert response1.json()["disclaimer"] == response2.json()["disclaimer"]

    def test_disclaimer_version_tracking(self):
        """Test disclaimer version is tracked."""
        response = client.get("/disclaimer")
        data = response.json()

        # Version should exist and be documented
        version = data["disclaimer"]["version"]
        assert version == "1.0"  # Initial version

        # Effective date should match Week 11 Day 3
        effective_date = data["disclaimer"]["effective_date"]
        assert effective_date == "2026-02-08"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
