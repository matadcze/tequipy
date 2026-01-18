"""Tests for weather service."""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "changeme-in-tests")

import pytest

from src.domain.exceptions import WeatherAPITimeoutError
from src.domain.services.weather_service import WeatherService
from src.infrastructure.weather.client import WeatherData


class TestWeatherService:
    """Tests for WeatherService."""

    @pytest.fixture
    def mock_client(self):
        """Create mock weather client."""
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_client, mock_cache):
        """Create service with mocked dependencies."""
        return WeatherService(
            weather_client=mock_client,
            cache=mock_cache,
        )

    @pytest.fixture
    def sample_weather_data(self):
        """Sample weather data from client."""
        return WeatherData(
            latitude=52.52,
            longitude=13.41,
            temperature_c=5.3,
            wind_speed_kmh=12.5,
            retrieved_at=datetime(2026, 1, 18, 10, 30, 0, tzinfo=timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_get_current_weather_cache_hit(self, service, mock_cache, sample_weather_data):
        """Test returning cached data."""
        mock_cache.get.return_value = sample_weather_data

        result = await service.get_current_weather(52.52, 13.41)

        assert result.latitude == 52.52
        assert result.longitude == 13.41
        assert result.temperature_c == 5.3
        assert result.from_cache is True
        mock_cache.get.assert_called_once_with(52.52, 13.41)

    @pytest.mark.asyncio
    async def test_get_current_weather_cache_miss(
        self, service, mock_client, mock_cache, sample_weather_data
    ):
        """Test fetching from upstream on cache miss."""
        mock_cache.get.return_value = None
        mock_client.get_current_weather.return_value = sample_weather_data

        result = await service.get_current_weather(52.52, 13.41)

        assert result.latitude == 52.52
        assert result.longitude == 13.41
        assert result.temperature_c == 5.3
        assert result.from_cache is False
        mock_client.get_current_weather.assert_called_once_with(52.52, 13.41)
        mock_cache.set.assert_called_once_with(sample_weather_data)

    @pytest.mark.asyncio
    async def test_get_current_weather_cache_set_failure(
        self, service, mock_client, mock_cache, sample_weather_data
    ):
        """Test that cache set failure doesn't break the request."""
        mock_cache.get.return_value = None
        mock_client.get_current_weather.return_value = sample_weather_data
        mock_cache.set.return_value = False  # Cache set fails

        result = await service.get_current_weather(52.52, 13.41)

        # Should still return the result
        assert result.latitude == 52.52
        assert result.from_cache is False

    @pytest.mark.asyncio
    async def test_get_current_weather_upstream_error(self, service, mock_client, mock_cache):
        """Test propagation of upstream errors."""
        mock_cache.get.return_value = None
        mock_client.get_current_weather.side_effect = WeatherAPITimeoutError("timeout")

        with pytest.raises(WeatherAPITimeoutError):
            await service.get_current_weather(52.52, 13.41)

        # Should not try to cache on error
        mock_cache.set.assert_not_called()
