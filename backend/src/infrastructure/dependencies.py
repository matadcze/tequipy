"""Dependency injection setup for infrastructure layer."""

from fastapi import Request

from src.domain.services import WeatherService


def get_weather_service(request: Request) -> WeatherService:
    """Get weather service instance with shared client and cache from app state."""
    return WeatherService(
        weather_client=request.app.state.weather_client,
        cache=request.app.state.weather_cache,
    )
