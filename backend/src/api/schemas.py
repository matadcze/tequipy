"""API request and response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Generic error schemas
class ErrorDetail(BaseModel):
    """Error detail information."""

    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail


# Health check schemas
class HealthResponse(BaseModel):
    """Health check response."""

    status: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    status: str
    components: Dict[str, str]


# Agent schemas
class AgentRunRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User prompt for the agent")
    system: Optional[str] = Field(None, description="Optional system guidance")
    tools: Optional[List[str]] = Field(None, description="Requested tools (future use)")


class AgentStep(BaseModel):
    step_type: str
    content: str


class AgentRunResponse(BaseModel):
    output: str
    steps: List[AgentStep]


# Weather schemas
class LocationResponse(BaseModel):
    """Geographic location coordinates."""

    lat: float = Field(..., description="Latitude coordinate", ge=-90, le=90)
    lon: float = Field(..., description="Longitude coordinate", ge=-180, le=180)


class CurrentWeatherResponse(BaseModel):
    """Current weather conditions."""

    temperatureC: float = Field(..., description="Temperature in Celsius")
    windSpeedKmh: float = Field(..., description="Wind speed in km/h")


class WeatherResponse(BaseModel):
    """Weather API response."""

    location: LocationResponse = Field(..., description="Location coordinates")
    current: CurrentWeatherResponse = Field(..., description="Current weather conditions")
    source: str = Field(default="open-meteo", description="Weather data source")
    retrievedAt: datetime = Field(..., description="Timestamp when data was retrieved")
