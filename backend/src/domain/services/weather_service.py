"""Weather service for fetching and caching weather data."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherResult:
    """Weather result with location and current conditions."""

    latitude: float
    longitude: float
    temperature_c: float
    wind_speed_kmh: float
    retrieved_at: datetime
    from_cache: bool


class WeatherDataProvider(Protocol):
    """Protocol for weather data providers."""

    async def get_current_weather(self, latitude: float, longitude: float) -> "WeatherDataResult":
        """Fetch current weather for the given coordinates."""
        ...


@dataclass(frozen=True)
class WeatherDataResult:
    """Raw weather data from provider."""

    latitude: float
    longitude: float
    temperature_c: float
    wind_speed_kmh: float
    retrieved_at: datetime


class WeatherCacheProvider(Protocol):
    """Protocol for weather cache implementations."""

    async def get(self, latitude: float, longitude: float) -> Optional[WeatherDataResult]:
        """Get cached weather data."""
        ...

    async def set(self, weather_data: WeatherDataResult) -> bool:
        """Cache weather data."""
        ...


class WeatherService:
    """Service for fetching weather data with caching support."""

    def __init__(
        self,
        weather_client: WeatherDataProvider,
        cache: WeatherCacheProvider,
    ):
        self.weather_client = weather_client
        self.cache = cache

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> WeatherResult:
        """
        Get current weather for the given coordinates.

        First checks cache, then fetches from upstream if not cached.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)

        Returns:
            WeatherResult with current conditions

        Raises:
            WeatherAPITimeoutError: If the upstream API times out
            WeatherAPIUnavailableError: If the upstream API is unavailable
        """
        # Try cache first
        cached = await self.cache.get(latitude, longitude)
        if cached is not None:
            logger.debug(f"Returning cached weather for lat={latitude}, lon={longitude}")
            return WeatherResult(
                latitude=cached.latitude,
                longitude=cached.longitude,
                temperature_c=cached.temperature_c,
                wind_speed_kmh=cached.wind_speed_kmh,
                retrieved_at=cached.retrieved_at,
                from_cache=True,
            )

        # Fetch from upstream
        logger.debug(f"Fetching fresh weather for lat={latitude}, lon={longitude}")
        weather_data = await self.weather_client.get_current_weather(latitude, longitude)

        # Cache the result (fire and forget - don't fail if cache fails)
        await self.cache.set(weather_data)

        return WeatherResult(
            latitude=weather_data.latitude,
            longitude=weather_data.longitude,
            temperature_c=weather_data.temperature_c,
            wind_speed_kmh=weather_data.wind_speed_kmh,
            retrieved_at=weather_data.retrieved_at,
            from_cache=False,
        )
