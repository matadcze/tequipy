# Tequipy Backend

Minimal API-only backend with Weather API, Agents endpoint, Health/Metrics, Redis-powered rate limiting, structured logging, and Prometheus metrics.

## Getting Started

1. Copy environment file:

```bash
cp .env.example .env
```

2. Install dependencies:

```bash
uv sync
```

3. Start Redis (required for rate limiting and caching):

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or use the full docker-compose stack from the repo root
```

4. Start the API:

```bash
uv run uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

## Developer Tooling

| Command                        | Description                              |
| ------------------------------ | ---------------------------------------- |
| `uv run pytest -v`             | Run all tests                            |
| `uv run pytest -k "test_name"` | Run tests matching pattern               |
| `make backend-lint`            | Lint check (ruff + black)                |
| `make backend-format`          | Auto-format (isort + black + ruff --fix) |
| `make backend-typecheck`       | Type check (mypy)                        |
| `make pre-commit`              | Run all pre-commit hooks                 |

## Project Layout

```
src/
├── api/            # FastAPI app, routers, middleware, schemas
│   ├── app.py      # App factory with lifespan, exception handlers
│   ├── v1/         # Versioned API routers
│   └── middleware/ # Rate limiting, logging, security headers
├── domain/         # Business logic, exceptions, service interfaces
│   └── services/   # WeatherService, AgentService
├── infrastructure/ # External integrations
│   ├── weather/    # Open-Meteo client and Redis cache
│   ├── agents/     # LLM provider abstraction
│   └── metrics/    # Prometheus metrics provider
└── core/           # Configuration, logging utilities
```

## API Endpoints

| Endpoint                            | Method | Description                          |
| ----------------------------------- | ------ | ------------------------------------ |
| `/api/v1/health`                    | GET    | Liveness check                       |
| `/api/v1/readiness`                 | GET    | Readiness check (Redis connectivity) |
| `/metrics`                          | GET    | Prometheus metrics                   |
| `/api/v1/weather/current?lat=&lon=` | GET    | Current weather (cached 60s)         |
| `/api/v1/agents/run`                | POST   | Agent execution (stub provider)      |
| `/api/docs`                         | GET    | OpenAPI documentation                |

## Configuration

Key environment variables (see `.env.example`):

| Variable                | Default                    | Description             |
| ----------------------- | -------------------------- | ----------------------- |
| `REDIS_URL`             | `redis://localhost:6379/0` | Redis connection URL    |
| `RATE_LIMIT_PER_MINUTE` | `100`                      | API rate limit per IP   |
| `LLM_PROVIDER`          | `stub`                     | LLM provider for agents |
| `DEBUG`                 | `false`                    | Enable debug mode       |

## Docker

From the repository root:

```bash
# Full stack (backend + redis + nginx + prometheus + grafana)
docker compose up -d --build

# Dev mode with hot reload
make docker-dev-up
```
