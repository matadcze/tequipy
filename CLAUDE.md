# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Minimal API-only backend with Weather API, Health/Metrics endpoints, Redis caching, and Prometheus/Grafana monitoring.

## Commands

### Development

```bash
make install              # Install all dependencies
make dev                  # Run backend (port 8000)
```

### Backend

```bash
make backend-install              # uv sync
make backend-dev                  # uvicorn with hot reload
cd backend && uv run pytest -v    # Run all tests
cd backend && uv run pytest tests/test_weather/test_weather_service.py -v  # Run single test file
cd backend && uv run pytest -k "test_cache_hit" -v  # Run tests matching pattern
make backend-lint                 # ruff check + black --check
make backend-format               # isort + black + ruff --fix
make backend-typecheck            # mypy
```

### Docker

```bash
docker compose up -d --build      # Full stack
make docker-dev-up                # Dev mode with hot reload
```

## Architecture

### Layered Structure (`backend/src/`)

- **api/**: FastAPI routers, middleware, Pydantic schemas. Entry point is `app.py` with `create_app()` factory.
- **domain/**: Business logic with no external dependencies. Services define behavior using Protocol-based interfaces.
- **infrastructure/**: Concrete implementations (Redis cache, HTTP clients, metrics). Implements domain Protocols.
- **core/**: Configuration (`config.py`), logging, shared utilities.

### Key Patterns

**Dependency Injection**: Services are injected via FastAPI's `Depends()`. Factory functions in `infrastructure/dependencies.py` wire implementations to domain interfaces.

**Protocol-based Interfaces**: Domain services depend on Protocols (e.g., `WeatherDataProvider`, `WeatherCacheProvider`), not concrete classes. Infrastructure provides implementations.

**App State for Shared Resources**: Long-lived resources (HTTP clients, Redis connections) are initialized in the lifespan context and stored in `app.state`. Services access them via `request.app.state`.

**Domain Exceptions**: All business errors extend `DomainException`. The app factory registers exception handlers that map these to appropriate HTTP status codes.

### Middleware Stack (order matters)

1. CORS
2. SecurityHeadersMiddleware
3. RateLimitMiddleware (Redis-backed, IP-based)
4. MetricsMiddleware (Prometheus counters)
5. RequestLoggingMiddleware (correlation IDs)

### Key Endpoints

- `/api/v1/health` - Liveness check
- `/api/v1/readiness` - Readiness check (Redis connectivity)
- `/metrics` - Prometheus metrics
- `/api/v1/weather/current?lat=&lon=` - Weather data (cached 60s)
- `/api/docs` - OpenAPI documentation

## Environment Setup

```bash
cp backend/.env.example backend/.env
```

Required: `REDIS_URL` (defaults to `redis://localhost:6379/0`)

For Docker: Redis is provided by compose. For local dev: run Redis separately.
