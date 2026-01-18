"""Dependency injection setup for infrastructure layer."""

from fastapi import Request

from src.domain.services import AgentService, WeatherService
from src.infrastructure.agents.providers import get_llm_provider


def get_agent_service() -> AgentService:
    """Get agent service instance."""
    provider = get_llm_provider()
    return AgentService(provider=provider)


def get_weather_service(request: Request) -> WeatherService:
    """Get weather service instance with shared client and cache from app state."""
    return WeatherService(
        weather_client=request.app.state.weather_client,
        cache=request.app.state.weather_cache,
    )
