"""Redis cache for weather data."""

import json
import logging
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from src.core.config import settings
from src.core.metrics import weather_cache_operations_total
from src.infrastructure.weather.client import WeatherData

logger = logging.getLogger(__name__)


class WeatherCache:
    """Redis-based cache for weather data with configurable TTL."""

    CACHE_KEY_PREFIX = "weather:current"

    def __init__(
        self,
        redis_url: str | None = None,
        ttl_seconds: int | None = None,
    ):
        self.redis_url = redis_url or settings.redis_url
        self.ttl_seconds = ttl_seconds or settings.weather_cache_ttl_seconds
        self._redis_client: Optional[Redis] = None

    async def _get_client(self) -> Redis:
        """Get or create the Redis client."""
        if self._redis_client is None:
            self._redis_client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8",
            )
        return self._redis_client

    async def close(self) -> None:
        """Close the Redis client."""
        if self._redis_client is not None:
            await self._redis_client.close()
            self._redis_client = None

    def _make_cache_key(self, latitude: float, longitude: float) -> str:
        """Generate cache key from coordinates (rounded to 2 decimal places)."""
        # Round to 2 decimal places for cache key to group nearby requests
        lat_key = f"{latitude:.2f}"
        lon_key = f"{longitude:.2f}"
        return f"{self.CACHE_KEY_PREFIX}:{lat_key}:{lon_key}"

    async def get(self, latitude: float, longitude: float) -> Optional[WeatherData]:
        """
        Get cached weather data for the given coordinates.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            Cached WeatherData or None if not found/expired
        """
        client = await self._get_client()
        key = self._make_cache_key(latitude, longitude)

        try:
            cached = await client.get(key)
            if cached is None:
                logger.debug(f"Cache miss for {key}")
                weather_cache_operations_total.labels(operation="get", result="miss").inc()
                return None

            data = json.loads(cached)
            logger.debug(f"Cache hit for {key}")
            weather_cache_operations_total.labels(operation="get", result="hit").inc()
            return WeatherData(
                latitude=data["latitude"],
                longitude=data["longitude"],
                temperature_c=data["temperature_c"],
                wind_speed_kmh=data["wind_speed_kmh"],
                retrieved_at=datetime.fromisoformat(data["retrieved_at"]),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Invalid cached data for {key}: {e}")
            weather_cache_operations_total.labels(operation="get", result="error").inc()
            # Delete corrupted cache entry
            await client.delete(key)
            return None

        except Exception as e:
            logger.error(f"Redis error getting cache for {key}: {e}")
            weather_cache_operations_total.labels(operation="get", result="error").inc()
            # Fail open - return None so we fetch fresh data
            return None

    async def set(self, weather_data: WeatherData) -> bool:
        """
        Cache weather data.

        Args:
            weather_data: Weather data to cache

        Returns:
            True if cached successfully, False otherwise
        """
        client = await self._get_client()
        key = self._make_cache_key(weather_data.latitude, weather_data.longitude)

        try:
            data = {
                "latitude": weather_data.latitude,
                "longitude": weather_data.longitude,
                "temperature_c": weather_data.temperature_c,
                "wind_speed_kmh": weather_data.wind_speed_kmh,
                "retrieved_at": weather_data.retrieved_at.isoformat(),
            }
            await client.setex(key, self.ttl_seconds, json.dumps(data))
            logger.debug(f"Cached weather data for {key} with TTL={self.ttl_seconds}s")
            weather_cache_operations_total.labels(operation="set", result="success").inc()
            return True

        except Exception as e:
            logger.error(f"Redis error setting cache for {key}: {e}")
            weather_cache_operations_total.labels(operation="set", result="error").inc()
            # Fail open - don't break the request
            return False
