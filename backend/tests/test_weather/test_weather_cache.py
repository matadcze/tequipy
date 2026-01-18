"""Tests for tiered weather cache (L1 in-memory + L2 Redis)."""

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
    """Tests for WeatherCache with tiered caching."""

    @pytest.fixture
    def cache(self):
        """Create cache with test settings."""
        return WeatherCache(
            redis_url="redis://localhost:6379/0",
            ttl_seconds=60,
            l1_max_size=100,
            l1_ttl_seconds=30,
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

    # L1 Cache Tests

    def test_l1_set_and_get(self, cache, sample_weather_data):
        """Test L1 cache set and get."""
        key = cache._make_cache_key(52.52, 13.41)

        # Set in L1
        cache._set_in_l1(key, sample_weather_data)

        # Get from L1
        result = cache._get_from_l1(key)

        assert result is not None
        assert result.latitude == 52.52
        assert result.temperature_c == 5.3

    def test_l1_miss(self, cache):
        """Test L1 cache miss."""
        key = cache._make_cache_key(99.99, 99.99)
        result = cache._get_from_l1(key)
        assert result is None

    def test_get_l1_stats(self, cache, sample_weather_data):
        """Test L1 stats retrieval."""
        key = cache._make_cache_key(52.52, 13.41)
        cache._set_in_l1(key, sample_weather_data)

        stats = cache.get_l1_stats()

        assert stats["size"] == 1
        assert stats["maxsize"] == 100
        assert stats["ttl"] == 30

    # L1 Hit Tests

    @pytest.mark.asyncio
    async def test_get_l1_hit(self, cache, sample_weather_data):
        """Test that L1 hit returns data without hitting Redis."""
        key = cache._make_cache_key(52.52, 13.41)

        # Pre-populate L1
        cache._set_in_l1(key, sample_weather_data)

        # Mock Redis to verify it's not called
        mock_redis = AsyncMock()
        with patch.object(cache, "_get_client", return_value=mock_redis):
            result = await cache.get(52.52, 13.41)

        # Should return L1 data without calling Redis
        assert result is not None
        assert result.latitude == 52.52
        mock_redis.get.assert_not_called()

    # L2 Hit Tests

    @pytest.mark.asyncio
    async def test_get_l2_hit_populates_l1(self, cache):
        """Test that L2 hit populates L1 cache."""
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

        # Verify L2 hit
        assert result is not None
        assert result.latitude == 52.52

        # Verify L1 was populated
        key = cache._make_cache_key(52.52, 13.41)
        l1_result = cache._get_from_l1(key)
        assert l1_result is not None
        assert l1_result.latitude == 52.52

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache):
        """Test cache miss (both L1 and L2)."""
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

    # Set Tests

    @pytest.mark.asyncio
    async def test_set_populates_both_tiers(self, cache, sample_weather_data):
        """Test that set populates both L1 and L2."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        with patch.object(cache, "_get_client", return_value=mock_redis):
            result = await cache.set(sample_weather_data)

        # Verify L2 was set
        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "weather:current:52.52:13.41"
        assert call_args[0][1] == 60  # TTL

        # Verify L1 was also set
        key = cache._make_cache_key(52.52, 13.41)
        l1_result = cache._get_from_l1(key)
        assert l1_result is not None
        assert l1_result.latitude == 52.52

    @pytest.mark.asyncio
    async def test_set_redis_error_still_sets_l1(self, cache, sample_weather_data):
        """Test that L1 is set even when Redis fails."""
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis connection error")

        with patch.object(cache, "_get_client", return_value=mock_redis):
            # Should fail open (return False, but L1 still set)
            result = await cache.set(sample_weather_data)

        assert result is False

        # L1 should still be populated
        key = cache._make_cache_key(52.52, 13.41)
        l1_result = cache._get_from_l1(key)
        assert l1_result is not None
        assert l1_result.latitude == 52.52

    # Close Tests

    @pytest.mark.asyncio
    async def test_close_clears_l1_and_redis(self, cache, sample_weather_data):
        """Test that close clears L1 and closes Redis."""
        # Populate L1
        key = cache._make_cache_key(52.52, 13.41)
        cache._set_in_l1(key, sample_weather_data)

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        cache._redis_client = mock_redis

        await cache.close()

        # Verify Redis was closed
        mock_redis.aclose.assert_called_once()
        assert cache._redis_client is None

        # Verify L1 was cleared
        l1_result = cache._get_from_l1(key)
        assert l1_result is None
