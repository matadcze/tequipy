"""Weather API endpoints."""

from fastapi import APIRouter, Depends, Query

from src.api.schemas import CurrentWeatherResponse, LocationResponse, WeatherResponse
from src.domain.services import WeatherService
from src.infrastructure.dependencies import get_weather_service

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get(
    "/current",
    response_model=WeatherResponse,
    summary="Get current weather",
    description="Fetch current temperature and wind speed for the given coordinates. "
    "Results are cached for 60 seconds.",
)
async def get_current_weather(
    lat: float = Query(
        ...,
        description="Latitude coordinate",
        ge=-90,
        le=90,
        examples=[52.52],
    ),
    lon: float = Query(
        ...,
        description="Longitude coordinate",
        ge=-180,
        le=180,
        examples=[13.41],
    ),
    weather_service: WeatherService = Depends(get_weather_service),
) -> WeatherResponse:
    """
    Get current weather for the given coordinates.

    - **lat**: Latitude (-90 to 90)
    - **lon**: Longitude (-180 to 180)

    Returns current temperature in Celsius and wind speed in km/h.
    Data is sourced from Open-Meteo API and cached for 60 seconds.
    """
    result = await weather_service.get_current_weather(lat, lon)

    return WeatherResponse(
        location=LocationResponse(lat=result.latitude, lon=result.longitude),
        current=CurrentWeatherResponse(
            temperatureC=result.temperature_c,
            windSpeedKmh=result.wind_speed_kmh,
        ),
        source="open-meteo",
        retrievedAt=result.retrieved_at,
    )
