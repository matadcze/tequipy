# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack application template with FastAPI backend and Next.js frontend. Features JWT authentication, audit logging, async SQLAlchemy, Celery workers, Redis rate limiting, and Prometheus/Grafana monitoring.

## Commands

### Development

```bash
make install              # Install all dependencies (backend + frontend)
make dev                  # Run backend (port 8000) and frontend (port 3000) in parallel
```

### Backend

```bash
make backend-install              # uv sync
make backend-dev                  # uvicorn with hot reload
cd backend && uv run alembic upgrade head   # Run migrations
cd backend && uv run pytest -v    # Run tests
make backend-lint                 # ruff check + black --check
make backend-format               # isort + black + ruff --fix
make backend-typecheck            # mypy
```

### Frontend

```bash
make frontend-install     # npm install
make frontend-dev         # next dev
make frontend-lint        # eslint
make frontend-format      # prettier
make frontend-test        # playwright e2e tests
```

### Docker

```bash
docker compose up -d --build      # Full stack
make docker-dev-up                # Dev mode with hot reload
```

### Utilities

```bash
make seed                 # Create fixture users (admin@example.com / ChangeMe123!)
make pre-commit-install   # Install git hooks
make pre-commit           # Run all pre-commit hooks
```

## Architecture

### Backend (`backend/src/`)

- **api/**: FastAPI app factory, routers (`v1/`), middleware, Pydantic schemas
- **domain/**: Business logic layer - entities, exceptions, repository interfaces, services
- **infrastructure/**: Implementation layer - database models/sessions, auth utilities, metrics, concrete repositories
- **worker/**: Celery configuration and tasks
- **core/**: Configuration and settings

Key endpoints: `/api/v1/health`, `/api/v1/readiness`, `/metrics`, `/api/v1/auth/*`, `/api/v1/audit`, `/api/v1/agents/run`

### Frontend (`frontend/src/`)

- **app/**: Next.js App Router pages (login, register, profile, dashboard, agents)
- **components/**: Reusable React components
- **lib/**: API client (`api/`), TypeScript types (`types/`), utilities (`utils/`)
- **contexts/**: React context providers
- **hooks/**: Custom React hooks
- **config/**: Application configuration
- **styles/**: Global styles (Tailwind CSS)

### Stack

- Backend: Python 3.12+, FastAPI, SQLAlchemy (async), Alembic, Celery, Redis
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Playwright
- Package managers: uv (backend), npm (frontend)

## Environment Setup

Copy and configure environment files before running:

```bash
cp backend/.env.example backend/.env    # Set DATABASE_URL, JWT_SECRET_KEY
cp frontend/.env.example frontend/.env  # Set NEXT_PUBLIC_API_URL
```

For local dev without Docker, use `NEXT_PUBLIC_API_URL=http://localhost:8000`.
