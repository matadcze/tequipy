"""Tests for weather cache."""

import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "changeme-in-tests")

import pytest

from src.infrastructure.weather.cache import WeatherCache
from src.infrastructure.weather.client import WeatherData


class TestWeatherCache:
    """Tests for WeatherCache."""

    @pytest.fixture
    def cache(self):
        """Create cache with test settings."""
        return WeatherCache(
            redis_url="redis://localhost:6379/0",
            ttl_seconds=60,
        )

    @pytest.fixture
    def sample_weather_data(self):
        """Sample weather data."""
        return WeatherData(
            latitude=52.52,
            longitude=13.41,
            temperature_c=5.3,
            wind_speed_kmh=12.5,
            retrieved_at=datetime(2026, 1, 18, 10, 30, 0, tzinfo=timezone.utc),
        )

    def test_make_cache_key(self, cache):
        """Test cache key generation."""
        key = cache._make_cache_key(52.52, 13.41)
        assert key == "weather:current:52.52:13.41"

    def test_make_cache_key_rounds_coordinates(self, cache):
        """Test that coordinates are rounded to 2 decimal places."""
        key = cache._make_cache_key(52.5234, 13.4156)
        assert key == "weather:current:52.52:13.42"

    def test_make_cache_key_negative_coords(self, cache):
        """Test cache key with negative coordinates."""
        key = cache._make_cache_key(-33.87, -151.21)
        assert key == "weather:current:-33.87:-151.21"

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache):
        """Test cache hit."""
        cached_data = {
            "latitude": 52.52,
            "longitude": 13.41,
            "temperature_c": 5.3,
            "wind_speed_kmh": 12.5,
            "retrieved_at": "2026-01-18T10:30:00+00:00",
        }

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(cached_data)

        with patch.object(cache, "_get_client", return_value=mock_redis):
            result = await cache.get(52.52, 13.41)

        assert result is not None
        assert result.latitude == 52.52
        assert result.longitude == 13.41
        assert result.temperature_c == 5.3
        assert result.wind_speed_kmh == 12.5

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache):
        """Test cache miss."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch.object(cache, "_get_client", return_value=mock_redis):
            result = await cache.get(52.52, 13.41)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_corrupted_cache_data(self, cache):
        """Test handling of corrupted cache data."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "not valid json"
        mock_redis.delete = AsyncMock()

        with patch.object(cache, "_get_client", return_value=mock_redis):
            result = await cache.get(52.52, 13.41)

        assert result is None
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_error(self, cache):
        """Test handling of Redis errors."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")

        with patch.object(cache, "_get_client", return_value=mock_redis):
            # Should fail open (return None, not raise)
            result = await cache.get(52.52, 13.41)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, cache, sample_weather_data):
        """Test successful cache set."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        with patch.object(cache, "_get_client", return_value=mock_redis):
            result = await cache.set(sample_weather_data)

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "weather:current:52.52:13.41"
        assert call_args[0][1] == 60  # TTL

    @pytest.mark.asyncio
    async def test_set_redis_error(self, cache, sample_weather_data):
        """Test handling of Redis errors on set."""
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis connection error")

        with patch.object(cache, "_get_client", return_value=mock_redis):
            # Should fail open (return False, not raise)
            result = await cache.set(sample_weather_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, cache):
        """Test client cleanup."""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        cache._redis_client = mock_redis

        await cache.close()

        mock_redis.close.assert_called_once()
        assert cache._redis_client is None
