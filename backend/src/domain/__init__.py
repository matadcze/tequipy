from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    DomainException,
    InternalError,
    NotFoundError,
    RateLimitExceeded,
    ValidationError,
    WeatherAPIError,
    WeatherAPITimeoutError,
    WeatherAPIUnavailableError,
)

__all__ = [
    "DomainException",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "RateLimitExceeded",
    "InternalError",
    "WeatherAPIError",
    "WeatherAPITimeoutError",
    "WeatherAPIUnavailableError",
]
