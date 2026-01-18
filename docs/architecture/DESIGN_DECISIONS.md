# Backend Design Decisions

This document outlines the deliberate architectural choices made for the Tequipy FastAPI backend. Each decision is justified with trade-off analysis and alternatives considered.

## Table of Contents

1. [Framework: FastAPI](#1-framework-fastapi)
2. [HTTP Client: httpx](#2-http-client-httpx)
3. [Caching: Tiered Strategy](#3-caching-tiered-strategy)
4. [Project Structure: Clean Architecture](#4-project-structure-clean-architecture)
5. [Database: Async SQLAlchemy](#5-database-async-sqlalchemy)
6. [Authentication: JWT with Refresh Tokens](#6-authentication-jwt-with-refresh-tokens)
7. [Task Queue: Celery with Redis](#7-task-queue-celery-with-redis)
8. [Observability: Prometheus + Structured Logging](#8-observability-prometheus--structured-logging)

---

## 1. Framework: FastAPI

### Decision

Use **FastAPI** as the web framework for the backend API.

### Rationale

| Requirement | FastAPI Capability |
|-------------|-------------------|
| **Async support** | Native async/await, built on Starlette ASGI |
| **Automatic OpenAPI docs** | Interactive Swagger UI + ReDoc at `/docs` and `/redoc` |
| **Pydantic validation** | Request/response validation with type hints |
| **Dependency injection** | Built-in `Depends()` system for clean DI |
| **Performance** | One of the fastest Python frameworks (Starlette + Uvicorn) |
| **Type safety** | Full mypy compatibility, excellent IDE support |

### Alternatives Considered

| Framework | Pros | Cons | Decision |
|-----------|------|------|----------|
| **Django + DRF** | Batteries included, mature ORM | Sync-first, heavy, slower | Rejected: Overkill for API-only service |
| **Flask** | Simple, lightweight | No async, no built-in validation | Rejected: Missing modern features |
| **Starlette** | Lightweight, fast | No validation, more manual work | Rejected: FastAPI adds value |
| **Litestar** | Feature-rich, fast | Smaller ecosystem, less battle-tested | Rejected: FastAPI more established |

### Key Implementation Patterns

```python
# App factory pattern (src/api/app.py)
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Register middleware in order
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Mount routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1/auth")

    return app
```

---

## 2. HTTP Client: httpx

### Decision

Use **httpx** with async support for all upstream HTTP calls.

### Rationale

- **Async-native**: Integrates seamlessly with FastAPI's async handlers
- **HTTP/2 support**: Multiplexed connections for modern APIs
- **requests-compatible API**: Familiar interface, easy migration
- **Built-in test client**: `httpx.AsyncClient` works as test client
- **Connection pooling**: Automatic keep-alive and connection reuse

### Configuration

```python
# Recommended client setup
import httpx

# Application-scoped client (created at startup, closed at shutdown)
async def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=5.0),
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
        ),
        http2=True,
        follow_redirects=True,
    )
```

### Timeout Strategy

| Operation Type | Connect | Read | Total | Rationale |
|---------------|---------|------|-------|-----------|
| Default | 5s | 25s | 30s | Most API calls |
| LLM Provider | 10s | 110s | 120s | LLM responses can be slow |
| Health Check | 2s | 3s | 5s | Fast fail for probes |
| Webhooks | 5s | 10s | 15s | External endpoints may be slow |

### Alternatives Considered

| Library | Async | HTTP/2 | Testing | API Familiarity |
|---------|-------|--------|---------|-----------------|
| **httpx** | Native | Yes | Built-in mock transport | requests-like |
| **aiohttp** | Native | No | External mocks | Different API |
| **requests** | No | No | External mocks | Familiar |

---

## 3. Caching: Tiered Strategy

### Decision

Implement **two-tier caching**: L1 (in-memory) + L2 (Redis).

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Request Flow                           │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     Miss      ┌─────────────┐     Miss    │
│  │ L1: TTLCache │ ──────────► │ L2: Redis   │ ──────────► │
│  │ (in-memory)  │              │ (distributed)│             │
│  └─────────────┘              └─────────────┘             │
│         │                           │                       │
│         │ Hit                       │ Hit                   │
│         ▼                           ▼                       │
│    Return immediately         Populate L1, Return           │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### L1 Cache: cachetools TTLCache

```python
from cachetools import TTLCache

# Per-service cache configuration
CACHE_CONFIG = {
    "user_profile": {"maxsize": 500, "ttl": 300},    # 5 min
    "rate_limits": {"maxsize": 10000, "ttl": 60},    # 1 min
    "config": {"maxsize": 100, "ttl": 600},          # 10 min
}
```

**Best for:**
- High-frequency reads (user sessions, rate limits)
- Single-instance deployments
- Data that can tolerate brief staleness

### L2 Cache: Redis

**Best for:**
- Multi-instance deployments (shared state)
- Expensive operations (LLM responses, external API calls)
- Data requiring distributed invalidation
- Larger cache sizes (Redis scales better than memory)

### Cache Invalidation Strategy

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| **TTL-based** | Most data | Set appropriate TTL per data type |
| **Write-through** | User profile updates | Update cache on write |
| **Cache-aside** | Reference data | Fetch on miss, cache result |
| **Event-driven** | Real-time consistency | Pub/sub invalidation |

---

## 4. Project Structure: Clean Architecture

### Decision

Adopt **layered architecture** with clear separation: API → Domain ← Infrastructure.

### Directory Structure

```
backend/src/
├── api/                    # HTTP layer (FastAPI-specific)
│   ├── app.py             # App factory, middleware registration
│   ├── schemas.py         # Pydantic request/response models
│   ├── middleware/        # Cross-cutting HTTP concerns
│   └── v1/                # Versioned API routes
│
├── domain/                 # Business logic (framework-agnostic)
│   ├── entities.py        # Domain models (pure Python/Pydantic)
│   ├── repositories.py    # Repository interfaces (ABCs)
│   ├── exceptions.py      # Domain-specific errors
│   ├── value_objects.py   # Enums, value types
│   └── services/          # Business logic services
│
├── infrastructure/         # Implementation details
│   ├── database/          # SQLAlchemy models, session management
│   ├── repositories/      # Concrete repository implementations
│   ├── auth/              # JWT, password hashing
│   ├── cache/             # Cache implementations (planned)
│   ├── http/              # HTTP client provider (planned)
│   └── dependencies.py    # FastAPI DI setup
│
├── worker/                 # Async task processing
│   ├── celery_app.py
│   └── tasks.py
│
└── core/                   # Shared utilities
    ├── config.py          # Settings from environment
    ├── logging.py         # Structured logging
    └── metrics.py         # Prometheus helpers
```

### Dependency Rule

```
            ┌──────────────┐
            │     API      │  ─── Depends on ───┐
            └──────────────┘                    │
                                                ▼
            ┌──────────────┐              ┌──────────────┐
            │   Domain     │ ◄─ Implements ─│Infrastructure│
            │ (Interfaces) │               │ (Concrete)   │
            └──────────────┘              └──────────────┘
```

The Domain layer has **zero** framework dependencies. It defines interfaces that Infrastructure implements.

### Key Benefits

1. **Testability**: Domain logic tested without database/HTTP
2. **Flexibility**: Swap infrastructure (e.g., PostgreSQL → MySQL) without changing domain
3. **Maintainability**: Clear boundaries reduce cognitive load
4. **Team scalability**: Different engineers can work on different layers

---

## 5. Database: Async SQLAlchemy

### Decision

Use **SQLAlchemy 2.0** with async support via **asyncpg** driver.

### Rationale

- **Async-native**: `AsyncSession` integrates with FastAPI's async handlers
- **Type safety**: SQLAlchemy 2.0's typed queries
- **Migration support**: Alembic for schema versioning
- **Connection pooling**: Built-in async connection pool

### Session Management

```python
# Dependency injection pattern
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Repository Pattern

```python
# Domain interface (no SQLAlchemy dependency)
class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

# Infrastructure implementation (SQLAlchemy-specific)
class UserRepositoryImpl(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        db_user = result.scalar_one_or_none()
        return User.model_validate(db_user) if db_user else None
```

---

## 6. Authentication: JWT with Refresh Tokens

### Decision

Implement **stateless JWT authentication** with short-lived access tokens and long-lived refresh tokens.

### Token Strategy

| Token Type | Lifetime | Storage | Purpose |
|------------|----------|---------|---------|
| Access Token | 15 min | Client memory | API authentication |
| Refresh Token | 7 days | Client (HTTP-only cookie) + DB hash | Token renewal |

### Security Measures

- **Access token**: Short expiry limits damage from token theft
- **Refresh token**: Stored as bcrypt hash in DB, single-use
- **Token rotation**: New refresh token issued on each refresh
- **Account lockout**: Failed login attempts tracked, lockout after N failures

### Flow

```
1. Login → Access Token + Refresh Token
2. API Call → Send Access Token in Authorization header
3. Access Token expires → Call /refresh with Refresh Token
4. Refresh → New Access Token + New Refresh Token (old invalidated)
5. Logout → Revoke Refresh Token
```

---

## 7. Task Queue: Celery with Redis

### Decision

Use **Celery** with **Redis** as message broker for background tasks.

### Use Cases

- Email sending
- Report generation
- Data aggregation
- Scheduled jobs (Celery Beat)

### Configuration

```python
celery_app = Celery(
    "tequipy",
    broker=settings.celery_broker_url,  # redis://
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # Reliability: ack after completion
)
```

---

## 8. Observability: Prometheus + Structured Logging

### Decision

Implement comprehensive observability with **Prometheus metrics** and **structured JSON logging**.

### Metrics

```python
# Custom business metrics
auth_operations = Counter(
    "auth_operations_total",
    "Authentication operations",
    ["operation", "status"]
)

# Endpoint metrics (via prometheus-fastapi-instrumentator)
# - http_requests_total
# - http_request_duration_seconds
# - http_requests_in_progress
```

### Logging

```python
# Structured log format
{
    "timestamp": "2025-01-18T10:30:00Z",
    "level": "INFO",
    "message": "User logged in",
    "correlation_id": "abc-123",
    "user_id": "uuid",
    "ip": "192.168.1.1",
    "duration_ms": 45
}
```

### Health Endpoints

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `/api/v1/health` | Liveness probe | App is running |
| `/api/v1/readiness` | Readiness probe | DB, Redis, Storage connected |
| `/metrics` | Prometheus scrape | All custom + HTTP metrics |

---

## Summary

These decisions prioritize:

1. **Developer experience**: Type safety, auto-docs, familiar APIs
2. **Performance**: Async-first, connection pooling, tiered caching
3. **Maintainability**: Clean architecture, clear boundaries
4. **Scalability**: Stateless auth, distributed cache, task queue
5. **Observability**: Metrics, structured logs, health checks

All decisions are documented in [Architecture Decision Records](../docs/adr/) for future reference and onboarding.
