"""Open-Meteo API client implementation."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx

from src.core.config import settings
from src.core.metrics import weather_requests_total, weather_upstream_duration_seconds
from src.domain.exceptions import WeatherAPITimeoutError, WeatherAPIUnavailableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherData:
    """Weather data from Open-Meteo API."""

    latitude: float
    longitude: float
    temperature_c: float
    wind_speed_kmh: float
    retrieved_at: datetime


class WeatherClient(Protocol):
    """Protocol for weather API clients."""

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        """Fetch current weather for the given coordinates."""
        ...


class OpenMeteoClient:
    """HTTP client for Open-Meteo API with configurable timeout."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.base_url = base_url or settings.weather_api_base
        self.timeout_seconds = timeout_seconds or settings.weather_api_timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        """
        Fetch current weather from Open-Meteo API.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)

        Returns:
            WeatherData with current temperature and wind speed

        Raises:
            WeatherAPITimeoutError: If the API request times out
            WeatherAPIUnavailableError: If the API is unavailable or returns an error
        """
        client = await self._get_client()
        url = f"{self.base_url}/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m",
        }

        start_time = time.perf_counter()
        try:
            logger.debug(f"Fetching weather for lat={latitude}, lon={longitude}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            duration = time.perf_counter() - start_time
            weather_upstream_duration_seconds.observe(duration)
            weather_requests_total.labels(status="success").inc()

            current = data.get("current", {})

            # Log warnings for missing fields to detect API format changes
            if "temperature_2m" not in current:
                logger.warning(
                    f"Missing temperature_2m in API response for lat={latitude}, lon={longitude}, using default 0.0"
                )
            if "wind_speed_10m" not in current:
                logger.warning(
                    f"Missing wind_speed_10m in API response for lat={latitude}, lon={longitude}, using default 0.0"
                )

            return WeatherData(
                latitude=data.get("latitude", latitude),
                longitude=data.get("longitude", longitude),
                temperature_c=current.get("temperature_2m", 0.0),
                wind_speed_kmh=current.get("wind_speed_10m", 0.0),
                retrieved_at=datetime.now(timezone.utc),
            )

        except httpx.TimeoutException as e:
            duration = time.perf_counter() - start_time
            weather_upstream_duration_seconds.observe(duration)
            weather_requests_total.labels(status="timeout").inc()
            logger.warning(f"Weather API timeout for lat={latitude}, lon={longitude}: {e}")
            raise WeatherAPITimeoutError(
                f"Weather API request timed out after {self.timeout_seconds}s"
            ) from e

        except httpx.HTTPStatusError as e:
            duration = time.perf_counter() - start_time
            weather_upstream_duration_seconds.observe(duration)
            weather_requests_total.labels(status="error").inc()
            logger.error(f"Weather API HTTP error: {e.response.status_code} - {e.response.text}")
            raise WeatherAPIUnavailableError(
                f"Weather API returned status {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            duration = time.perf_counter() - start_time
            weather_upstream_duration_seconds.observe(duration)
            weather_requests_total.labels(status="error").inc()
            logger.error(f"Weather API request error: {e}")
            raise WeatherAPIUnavailableError(f"Weather API request failed: {e}") from e
