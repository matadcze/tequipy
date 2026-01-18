class DomainException(Exception):
    pass


class ValidationError(DomainException):
    pass


class AuthenticationError(DomainException):
    pass


class AuthorizationError(DomainException):
    pass


class NotFoundError(DomainException):
    pass


class RateLimitExceeded(DomainException):
    pass


class InternalError(DomainException):
    pass


class WeatherAPIError(DomainException):
    """Base exception for weather API errors."""

    pass


class WeatherAPITimeoutError(WeatherAPIError):
    """Raised when the weather API request times out."""

    pass


class WeatherAPIUnavailableError(WeatherAPIError):
    """Raised when the weather API is unavailable."""

    pass
