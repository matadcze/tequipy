"""Tiered cache for weather data: L1 (in-memory) + L2 (Redis)."""

import json
import logging
from datetime import datetime
from threading import Lock
from typing import Optional

import redis.asyncio as aioredis
from cachetools import TTLCache
from redis.asyncio import Redis

from src.core.config import settings
from src.core.metrics import weather_cache_operations_total
from src.infrastructure.weather.client import WeatherData

logger = logging.getLogger(__name__)


class WeatherCache:
    """
    Two-tier cache for weather data.

    L1: In-memory TTLCache (fast, per-instance, short TTL)
    L2: Redis cache (shared across instances, longer TTL)

    Read path: L1 -> L2 -> miss
    Write path: L1 + L2 (write-through)
    """

    CACHE_KEY_PREFIX = "weather:current"

    # L1 cache settings
    L1_MAX_SIZE = 1000  # Maximum entries in memory
    L1_TTL_SECONDS = 30  # Shorter TTL for L1

    def __init__(
        self,
        redis_url: str | None = None,
        ttl_seconds: int | None = None,
        l1_max_size: int | None = None,
        l1_ttl_seconds: int | None = None,
    ):
        # L2 (Redis) settings
        self.redis_url = redis_url or settings.redis_url
        self.ttl_seconds = ttl_seconds or settings.weather_cache_ttl_seconds
        self._redis_client: Optional[Redis] = None

        # L1 (in-memory) cache
        l1_size = l1_max_size or self.L1_MAX_SIZE
        l1_ttl = l1_ttl_seconds or self.L1_TTL_SECONDS
        self._l1_cache: TTLCache = TTLCache(maxsize=l1_size, ttl=l1_ttl)
        self._l1_lock = Lock()  # Thread-safe access to L1

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
        """Close the Redis client and clear L1 cache."""
        if self._redis_client is not None:
            await self._redis_client.aclose()
            self._redis_client = None
        with self._l1_lock:
            self._l1_cache.clear()

    def _make_cache_key(self, latitude: float, longitude: float) -> str:
        """Generate cache key from coordinates (rounded to 2 decimal places)."""
        lat_key = f"{latitude:.2f}"
        lon_key = f"{longitude:.2f}"
        return f"{self.CACHE_KEY_PREFIX}:{lat_key}:{lon_key}"

    def _get_from_l1(self, key: str) -> Optional[WeatherData]:
        """Get data from L1 (in-memory) cache."""
        with self._l1_lock:
            return self._l1_cache.get(key)

    def _set_in_l1(self, key: str, data: WeatherData) -> None:
        """Set data in L1 (in-memory) cache."""
        with self._l1_lock:
            self._l1_cache[key] = data

    async def get(self, latitude: float, longitude: float) -> Optional[WeatherData]:
        """
        Get cached weather data using tiered lookup.

        Lookup order:
        1. Check L1 (in-memory) - fastest
        2. Check L2 (Redis) - if hit, populate L1
        3. Return None on miss

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            Cached WeatherData or None if not found/expired
        """
        key = self._make_cache_key(latitude, longitude)

        # Check L1 (in-memory) first
        l1_data = self._get_from_l1(key)
        if l1_data is not None:
            logger.debug(f"L1 cache hit for {key}")
            weather_cache_operations_total.labels(operation="get", result="l1_hit").inc()
            return l1_data

        # Check L2 (Redis)
        try:
            client = await self._get_client()
            cached = await client.get(key)

            if cached is None:
                logger.debug(f"Cache miss for {key}")
                weather_cache_operations_total.labels(operation="get", result="miss").inc()
                return None

            data = json.loads(cached)
            weather_data = WeatherData(
                latitude=data["latitude"],
                longitude=data["longitude"],
                temperature_c=data["temperature_c"],
                wind_speed_kmh=data["wind_speed_kmh"],
                retrieved_at=datetime.fromisoformat(data["retrieved_at"]),
            )

            # Populate L1 on L2 hit
            self._set_in_l1(key, weather_data)
            logger.debug(f"L2 cache hit for {key}, populated L1")
            weather_cache_operations_total.labels(operation="get", result="l2_hit").inc()
            return weather_data

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Invalid cached data for {key}: {e}")
            weather_cache_operations_total.labels(operation="get", result="error").inc()
            # Delete corrupted cache entry
            try:
                client = await self._get_client()
                await client.delete(key)
            except Exception:
                pass
            return None

        except Exception as e:
            logger.error(f"Redis error getting cache for {key}: {e}")
            weather_cache_operations_total.labels(operation="get", result="error").inc()
            # Fail open - return None so we fetch fresh data
            return None

    async def set(self, weather_data: WeatherData) -> bool:
        """
        Cache weather data in both tiers (write-through).

        Args:
            weather_data: Weather data to cache

        Returns:
            True if cached successfully in L2, False otherwise
        """
        key = self._make_cache_key(weather_data.latitude, weather_data.longitude)

        # Always set in L1 (fast, local)
        self._set_in_l1(key, weather_data)

        # Set in L2 (Redis)
        try:
            client = await self._get_client()
            data = {
                "latitude": weather_data.latitude,
                "longitude": weather_data.longitude,
                "temperature_c": weather_data.temperature_c,
                "wind_speed_kmh": weather_data.wind_speed_kmh,
                "retrieved_at": weather_data.retrieved_at.isoformat(),
            }
            await client.setex(key, self.ttl_seconds, json.dumps(data))
            logger.debug(f"Cached weather data for {key} (L1+L2, TTL={self.ttl_seconds}s)")
            weather_cache_operations_total.labels(operation="set", result="success").inc()
            return True

        except Exception as e:
            logger.error(f"Redis error setting cache for {key}: {e}")
            weather_cache_operations_total.labels(operation="set", result="error").inc()
            # L1 is still populated, so partial success
            return False

    def get_l1_stats(self) -> dict:
        """Get L1 cache statistics for monitoring."""
        with self._l1_lock:
            return {
                "size": len(self._l1_cache),
                "maxsize": self._l1_cache.maxsize,
                "ttl": self._l1_cache.ttl,
                "hits": getattr(self._l1_cache, "hits", None),
                "misses": getattr(self._l1_cache, "misses", None),
            }
