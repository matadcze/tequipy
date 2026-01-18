# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Minimal API-only backend with Weather API, Agents endpoint, Health/Metrics endpoints, Redis caching, and Prometheus/Grafana monitoring.

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
cd backend && uv run pytest -v    # Run tests
make backend-lint                 # ruff check + black --check
make backend-format               # isort + black + ruff --fix
make backend-typecheck            # mypy
```

### Docker

```bash
docker compose up -d --build      # Full stack
make docker-dev-up                # Dev mode with hot reload
```

### Utilities

```bash
make pre-commit-install   # Install git hooks
make pre-commit           # Run all pre-commit hooks
```

## Architecture

### Backend (`backend/src/`)

- **api/**: FastAPI app factory, routers (`v1/`), middleware, Pydantic schemas
- **domain/**: Business logic layer - exceptions, services
- **infrastructure/**: Implementation layer - agents, weather client, metrics
- **core/**: Configuration and settings

Key endpoints: `/api/v1/health`, `/api/v1/readiness`, `/metrics`, `/api/v1/weather/current`, `/api/v1/agents/run`

### Stack

- Backend: Python 3.12+, FastAPI, Redis
- Package manager: uv
- Monitoring: Prometheus, Grafana

## Environment Setup

Copy and configure environment files before running:

```bash
cp backend/.env.example backend/.env
```

For local dev without Docker, ensure Redis is running and set `REDIS_URL=redis://localhost:6379/0`.
