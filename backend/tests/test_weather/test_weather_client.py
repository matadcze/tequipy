"""Tests for Open-Meteo weather client."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "changeme-in-tests")

import httpx
import pytest

from src.domain.exceptions import WeatherAPITimeoutError, WeatherAPIUnavailableError
from src.infrastructure.weather.client import OpenMeteoClient


class MockResponse:
    """Mock HTTP response."""

    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(self.status_code),
            )


class TestOpenMeteoClient:
    """Tests for OpenMeteoClient."""

    @pytest.fixture
    def client(self):
        """Create client with test settings."""
        return OpenMeteoClient(
            base_url="https://api.open-meteo.com/v1",
            timeout_seconds=1.0,
        )

    @pytest.fixture
    def sample_response(self):
        """Sample Open-Meteo API response."""
        return {
            "latitude": 52.52,
            "longitude": 13.41,
            "current": {
                "temperature_2m": 5.3,
                "wind_speed_10m": 12.5,
            },
        }

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, client, sample_response):
        """Test successful weather fetch."""
        mock_response = MockResponse(sample_response)
        mock_get = AsyncMock(return_value=mock_response)

        with patch.object(httpx.AsyncClient, "get", mock_get):
            result = await client.get_current_weather(52.52, 13.41)

        assert result.latitude == 52.52
        assert result.longitude == 13.41
        assert result.temperature_c == 5.3
        assert result.wind_speed_kmh == 12.5
        assert isinstance(result.retrieved_at, datetime)

    @pytest.mark.asyncio
    async def test_get_current_weather_timeout(self, client):
        """Test timeout handling."""
        with patch.object(httpx.AsyncClient, "get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(WeatherAPITimeoutError) as exc_info:
                await client.get_current_weather(52.52, 13.41)

            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_weather_http_error(self, client):
        """Test HTTP error handling."""
        mock_response = MockResponse({}, status_code=500)
        with patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=mock_response)):
            with pytest.raises(WeatherAPIUnavailableError) as exc_info:
                await client.get_current_weather(52.52, 13.41)

            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_weather_connection_error(self, client):
        """Test connection error handling."""
        with patch.object(
            httpx.AsyncClient,
            "get",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            with pytest.raises(WeatherAPIUnavailableError) as exc_info:
                await client.get_current_weather(52.52, 13.41)

            assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_current_weather_missing_fields(self, client):
        """Test handling of incomplete API response."""
        incomplete_response = {
            "latitude": 52.52,
            "longitude": 13.41,
            "current": {},
        }
        mock_response = MockResponse(incomplete_response)
        with patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=mock_response)):
            result = await client.get_current_weather(52.52, 13.41)

            # Should default to 0.0 for missing fields
            assert result.temperature_c == 0.0
            assert result.wind_speed_kmh == 0.0

    @pytest.mark.asyncio
    async def test_client_close(self, client):
        """Test client cleanup."""
        # Force client creation with a mock
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        client._client = mock_client

        await client.close()

        mock_client.aclose.assert_called_once()
        assert client._client is None
