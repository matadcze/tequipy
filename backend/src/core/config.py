"""Application configuration settings."""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    # Application Information
    app_name: str = "Tequipy API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Rate Limiting
    rate_limit_per_minute: int = 100

    # Security Headers
    enable_hsts: bool = False  # Set to True in production when behind HTTPS

    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost",
        "http://localhost:8000",
    ]

    # File uploads (used by readiness check)
    upload_dir: Path = Path("uploads")

    # Weather API settings (Open-Meteo)
    weather_api_base: str = "https://api.open-meteo.com/v1"
    weather_api_timeout_seconds: float = 1.0
    weather_cache_ttl_seconds: int = 60

    def model_post_init(self, __context):
        """Post-initialization hook to set derived values."""
        # Always allow localhost (port 80) for Nginx in local/dev setups
        if "http://localhost" not in self.cors_origins:
            object.__setattr__(self, "cors_origins", [*self.cors_origins, "http://localhost"])
        # Ensure upload directory exists for basic readiness checks
        self.upload_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
