# Tequipy

Minimal API-only backend with Weather API, Health/Metrics endpoints, Redis caching, and Prometheus/Grafana monitoring.

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **Docker & Docker Compose** (for containerized setup)
- **Redis** (for local development without Docker)

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd tequipy

# Create environment file
cp backend/.env.example backend/.env

# Start all services
docker compose up -d --build

# Verify services are running
docker compose ps
```

Services will be available at:
| Service | URL |
|---------|-----|
| API Gateway | http://localhost |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost/api/docs |
| Prometheus | http://localhost:9091 |
| Grafana | http://localhost:3001 (admin/admin) |

### Option 2: Local Development

```bash
# Install dependencies
make install

# Start Redis (required)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Create environment file for local dev
cp backend/.env.example backend/.env
# Edit backend/.env and set: REDIS_URL=redis://localhost:6379/0

# Run the backend with hot reload
make dev
```

Backend will be available at http://localhost:8000

## API Endpoints

| Endpoint                            | Method | Description                       |
| ----------------------------------- | ------ | --------------------------------- |
| `/api/v1/health`                    | GET    | Liveness check                    |
| `/api/v1/readiness`                 | GET    | Readiness check (verifies Redis)  |
| `/api/v1/weather/current?lat=&lon=` | GET    | Current weather data (cached 60s) |
| `/api/docs`                         | GET    | OpenAPI/Swagger documentation     |
| `/metrics`                          | GET    | Prometheus metrics                |

### Example: Get Weather

```bash
curl "http://localhost:8000/api/v1/weather/current?lat=52.52&lon=13.41"
```

## Development Commands

```bash
make help                 # Show all available commands

# Development
make install              # Install all dependencies
make dev                  # Run backend with hot reload (port 8000)

# Testing & Quality
make test                 # Run tests
make lint                 # Run linters (ruff, black)
make format               # Auto-format code
make backend-typecheck    # Run mypy type checking

# Docker
make docker-build         # Build Docker images
make docker-up            # Start containers
make docker-down          # Stop containers
make docker-dev-up        # Dev mode with hot reload
```

## Running Tests

```bash
# Run all tests
cd backend && uv run pytest -v

# Run specific test file
cd backend && uv run pytest tests/test_weather/test_weather_service.py -v

# Run tests matching pattern
cd backend && uv run pytest -k "test_cache" -v
```

## Project Structure

```
tequipy/
├── backend/
│   ├── src/
│   │   ├── api/          # FastAPI routers, middleware, schemas
│   │   ├── domain/       # Business logic, protocols, exceptions
│   │   ├── infrastructure/  # Redis, HTTP clients, implementations
│   │   └── core/         # Configuration, logging, utilities
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── nginx/                # Reverse proxy configuration
├── prometheus/           # Monitoring configuration
├── grafana/              # Dashboard provisioning
├── k8s/                  # Kubernetes manifests
├── docker-compose.yml
└── Makefile
```

## Architecture

The backend follows a layered architecture with dependency injection:

- **API Layer**: FastAPI routers and middleware
- **Domain Layer**: Business logic with Protocol-based interfaces
- **Infrastructure Layer**: Concrete implementations (Redis, HTTP clients)

Key patterns:

- Protocol-based dependency injection via FastAPI's `Depends()`
- App state for shared resources (HTTP clients, Redis connections)
- Domain exceptions mapped to HTTP status codes

## Environment Variables

| Variable                | Default                | Description           |
| ----------------------- | ---------------------- | --------------------- |
| `REDIS_URL`             | `redis://redis:6379/0` | Redis connection URL  |
| `DEBUG`                 | `false`                | Enable debug mode     |
| `RATE_LIMIT_PER_MINUTE` | `100`                  | API rate limit per IP |
| `CORS_ORIGINS`          | `["http://localhost"]` | Allowed CORS origins  |

## Monitoring

### Prometheus

Access at http://localhost:9091

Pre-configured to scrape:

- Backend `/metrics` endpoint
- Request latency, count, and error rates

### Grafana

Access at http://localhost:3001 (admin/admin)

Pre-provisioned dashboards for API metrics visualization.

## Kubernetes Deployment

```bash
# Validate manifests
kustomize build k8s | kubeconform -strict

# Deploy to cluster
kubectl apply -k k8s/

# Check status
kubectl -n tequipy get pods
```

See `k8s/` directory for deployment manifests.

## License

MIT
