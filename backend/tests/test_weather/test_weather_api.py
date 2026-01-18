"""Tests for weather API endpoints - validation and error responses."""

import os

# Provide minimal defaults so the app can start in test environments
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "changeme-in-tests")

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture(scope="module")
def client():
    """Create test client with lifespan context for app.state initialization."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestWeatherValidation:
    """Tests for weather API parameter validation."""

    def test_get_current_weather_missing_lat(self, client):
        """Test that lat parameter is required."""
        response = client.get("/api/v1/weather/current?lon=13.41")

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "ValidationError"

    def test_get_current_weather_missing_lon(self, client):
        """Test that lon parameter is required."""
        response = client.get("/api/v1/weather/current?lat=52.52")

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "ValidationError"

    def test_get_current_weather_missing_both_params(self, client):
        """Test that both parameters are required."""
        response = client.get("/api/v1/weather/current")

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "ValidationError"

    def test_get_current_weather_invalid_lat_too_high(self, client):
        """Test lat > 90 is rejected."""
        response = client.get("/api/v1/weather/current?lat=91&lon=13.41")
        assert response.status_code == 422

    def test_get_current_weather_invalid_lat_too_low(self, client):
        """Test lat < -90 is rejected."""
        response = client.get("/api/v1/weather/current?lat=-91&lon=13.41")
        assert response.status_code == 422

    def test_get_current_weather_invalid_lon_too_high(self, client):
        """Test lon > 180 is rejected."""
        response = client.get("/api/v1/weather/current?lat=52.52&lon=181")
        assert response.status_code == 422

    def test_get_current_weather_invalid_lon_too_low(self, client):
        """Test lon < -180 is rejected."""
        response = client.get("/api/v1/weather/current?lat=52.52&lon=-181")
        assert response.status_code == 422

    def test_get_current_weather_invalid_lat_type(self, client):
        """Test non-numeric lat is rejected."""
        response = client.get("/api/v1/weather/current?lat=abc&lon=13.41")
        assert response.status_code == 422

    def test_get_current_weather_invalid_lon_type(self, client):
        """Test non-numeric lon is rejected."""
        response = client.get("/api/v1/weather/current?lat=52.52&lon=xyz")
        assert response.status_code == 422


class TestWeatherEndpointExists:
    """Tests to verify weather endpoint is registered."""

    def test_weather_endpoint_exists(self, client):
        """Test that the weather endpoint is registered (may fail with 502 if no Redis)."""
        response = client.get("/api/v1/weather/current?lat=0&lon=0")
        # Should be 200, 502 (upstream error), or 503 - but NOT 404
        assert response.status_code != 404
