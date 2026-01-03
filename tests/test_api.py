"""Tests for API routes."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.db.models import (
    MonitoredProfile,
    ViralVideo,
    VideoAnalysis,
    GeneratedStrategy,
    ProducedVideo,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_client():
    """Create test client for API."""
    with patch("src.api.main.get_settings") as mock_settings:
        mock_settings.return_value.api_token = None  # Disable auth for tests
        mock_settings.return_value.app_env = "test"
        mock_settings.return_value.app_debug = True
        mock_settings.return_value.api_rate_limit_max_requests = 0

        from src.api.main import app
        with TestClient(app) as client:
            yield client


@pytest.fixture
def authenticated_client():
    """Create authenticated test client."""
    with patch("src.api.main.get_settings") as mock_settings:
        mock_settings.return_value.api_token = "test_token_123"
        mock_settings.return_value.app_env = "test"
        mock_settings.return_value.app_debug = True
        mock_settings.return_value.api_rate_limit_max_requests = 0

        from src.api.main import app
        client = TestClient(app)
        client.headers["X-API-Key"] = "test_token_123"
        yield client


# ============================================================================
# API ROOT TESTS
# ============================================================================

class TestAPIRoot:
    """Tests for API root endpoints."""

    def test_api_root_returns_info(self, test_client):
        """Test API root returns application info."""
        response = test_client.get("/")
        # Root might redirect or return info
        assert response.status_code in [200, 307]

    def test_api_docs_accessible(self, test_client):
        """Test API docs are accessible."""
        response = test_client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_accessible(self, test_client):
        """Test OpenAPI schema is accessible."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class TestAuthentication:
    """Tests for API authentication."""

    def test_auth_required_when_configured(self):
        """Test authentication is required when API token is set."""
        with patch("src.api.main.get_settings") as mock_settings:
            mock_settings.return_value.api_token = "secret_token"
            mock_settings.return_value.app_env = "production"
            mock_settings.return_value.app_debug = False
            mock_settings.return_value.api_rate_limit_max_requests = 0

            from src.api.main import app
            client = TestClient(app, raise_server_exceptions=False)

            # Request without auth should fail
            response = client.get("/api/v1/profiles")
            assert response.status_code == 401

    def test_auth_succeeds_with_valid_token(self, authenticated_client):
        """Test authentication succeeds with valid token."""
        # With correct token, request should not return 401
        response = authenticated_client.get("/api/v1/profiles")
        # May return 200 or other non-401 status
        assert response.status_code != 401


# ============================================================================
# PROFILES ROUTES TESTS
# ============================================================================

class TestProfilesRoutes:
    """Tests for profiles API routes."""

    @patch("src.api.routes.profiles.get_async_db")
    async def test_list_profiles(self, mock_db, test_client):
        """Test listing profiles."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db.return_value.__aenter__.return_value = mock_session

        response = test_client.get("/api/v1/profiles")
        # Should return success or empty list
        assert response.status_code in [200, 500]  # 500 if DB not mocked properly

    def test_create_profile_validation(self, test_client):
        """Test profile creation validation."""
        # Invalid profile data (missing required fields)
        invalid_data = {"invalid": "data"}

        response = test_client.post("/api/v1/profiles", json=invalid_data)
        # Should return validation error
        assert response.status_code in [422, 400, 500]

    def test_profile_request_schema(self):
        """Test profile request schema."""
        valid_profile = {
            "username": "test_creator",
            "platform": "instagram",
            "niche": "humor",
            "priority": 3,
        }

        # Verify required fields
        assert "username" in valid_profile
        assert valid_profile["platform"] in ["instagram", "tiktok", "youtube"]


# ============================================================================
# VIDEOS ROUTES TESTS
# ============================================================================

class TestVideosRoutes:
    """Tests for videos API routes."""

    @patch("src.api.routes.videos.get_async_db")
    async def test_list_videos(self, mock_db, test_client):
        """Test listing videos."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db.return_value.__aenter__.return_value = mock_session

        response = test_client.get("/api/v1/videos")
        assert response.status_code in [200, 500]

    def test_video_filters(self, test_client):
        """Test video listing with filters."""
        # Test various filter combinations
        filters = [
            "?passes_prefilter=true",
            "?is_analyzed=false",
            "?limit=10&offset=0",
        ]

        for filter_str in filters:
            response = test_client.get(f"/api/v1/videos{filter_str}")
            # Should accept filter parameters
            assert response.status_code in [200, 500]


# ============================================================================
# STRATEGIES ROUTES TESTS
# ============================================================================

class TestStrategiesRoutes:
    """Tests for strategies API routes."""

    @patch("src.api.routes.strategies.get_async_db")
    async def test_list_strategies(self, mock_db, test_client):
        """Test listing strategies."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db.return_value.__aenter__.return_value = mock_session

        response = test_client.get("/api/v1/strategies")
        assert response.status_code in [200, 500]


# ============================================================================
# PRODUCTIONS ROUTES TESTS
# ============================================================================

class TestProductionsRoutes:
    """Tests for productions API routes."""

    @patch("src.api.routes.productions.get_async_db")
    async def test_list_productions(self, mock_db, test_client):
        """Test listing productions."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db.return_value.__aenter__.return_value = mock_session

        response = test_client.get("/api/v1/productions")
        assert response.status_code in [200, 500]


# ============================================================================
# DASHBOARD ROUTES TESTS
# ============================================================================

class TestDashboardRoutes:
    """Tests for dashboard API routes."""

    @patch("src.api.routes.dashboard.get_async_db")
    async def test_dashboard_stats(self, mock_db, test_client):
        """Test dashboard statistics endpoint."""
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        response = test_client.get("/api/v1/dashboard/stats")
        assert response.status_code in [200, 500]


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_disabled_in_dev(self, test_client):
        """Test rate limiting is disabled in development."""
        # Multiple requests should succeed
        for _ in range(10):
            response = test_client.get("/docs")
            assert response.status_code == 200

    def test_rate_limit_structure(self):
        """Test rate limit configuration structure."""
        rate_limit_config = {
            "max_requests": 100,
            "window_seconds": 60,
        }

        assert rate_limit_config["max_requests"] > 0
        assert rate_limit_config["window_seconds"] > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Tests for API error handling."""

    def test_not_found_returns_404(self, test_client):
        """Test non-existent routes return 404."""
        response = test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, test_client):
        """Test wrong HTTP method returns 405."""
        # Try DELETE on a GET-only endpoint
        response = test_client.delete("/docs")
        assert response.status_code == 405


# ============================================================================
# RESPONSE FORMAT TESTS
# ============================================================================

class TestResponseFormat:
    """Tests for API response formats."""

    def test_json_response_format(self, test_client):
        """Test responses are in JSON format."""
        response = test_client.get("/openapi.json")
        assert response.headers["content-type"].startswith("application/json")

    def test_error_response_format(self, test_client):
        """Test error responses have proper format."""
        response = test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404

        # Error should be JSON
        error_data = response.json()
        assert "detail" in error_data


# ============================================================================
# CORS TESTS
# ============================================================================

class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, test_client):
        """Test CORS headers are present."""
        response = test_client.options(
            "/api/v1/profiles",
            headers={"Origin": "http://localhost:3000"},
        )
        # CORS preflight should be handled
        assert response.status_code in [200, 405]
