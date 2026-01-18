# Cross-Cutting Concerns

## Overview

This document describes the cross-cutting concerns that span multiple layers and components of the Tequipy platform.

## Error Handling

### Backend Error Hierarchy

```
DomainException (400)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── NotFoundError (404)
├── ValidationError (422)
└── RateLimitExceeded (429)
```

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "AuthenticationError",
    "message": "Invalid email or password",
    "details": {},
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Exception Handling Flow

```mermaid
graph TD
    A[Request] --> B[Middleware]
    B --> C[Router]
    C --> D[Service]
    D -->|Success| E[Response]
    D -->|Domain Exception| F[Exception Handler]
    D -->|Unexpected Error| G[Generic Handler]
    F --> H[Formatted Error Response]
    G --> I[500 Error Response]
    H --> J[Log + Metrics]
    I --> J
```

### Backend Implementation

```python
# domain/exceptions.py
class DomainException(Exception):
    """Base exception for domain errors."""
    pass

class AuthenticationError(DomainException):
    """Invalid credentials or token."""
    pass

class NotFoundError(DomainException):
    """Resource not found."""
    pass

# api/app.py - Exception handlers
@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc):
    status_code = {
        AuthenticationError: 401,
        AuthorizationError: 403,
        NotFoundError: 404,
        RateLimitExceeded: 429,
    }.get(type(exc), 400)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": type(exc).__name__,
                "message": str(exc),
                "details": {},
                "correlation_id": get_correlation_id()
            }
        }
    )
```

### Frontend Error Handling

```typescript
// lib/api/client.ts
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: ErrorResponse,
    public correlationId?: string
  ) {
    super(message);
  }
}

// Usage in components
try {
  await apiClient.auth.login({ email, password });
} catch (error) {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        setError("Invalid credentials");
        break;
      case 429:
        setError("Too many attempts. Please wait.");
        break;
      default:
        setError(getFriendlyErrorMessage(error, "Login failed"));
    }
  }
}
```

---

## Logging

### Logging Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application                               │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   Middleware  │  │    Services   │  │    Workers    │       │
│  │    Logging    │  │    Logging    │  │    Logging    │       │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘       │
│          │                  │                  │                │
│          └──────────────────┼──────────────────┘                │
│                             ▼                                   │
│                    ┌───────────────┐                           │
│                    │  JSON Logger  │                           │
│                    │  (structlog)  │                           │
│                    └───────┬───────┘                           │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             ▼
                    ┌───────────────┐
                    │    stdout     │
                    │  (container)  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Log Collector │
                    │ (CloudWatch,  │
                    │  ELK, etc.)   │
                    └───────────────┘
```

### Structured JSON Logging

```python
# core/logging.py
def log_json(logger, event: str, **kwargs):
    """Log structured JSON event."""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "correlation_id": get_correlation_id(),
        **kwargs
    }
    logger.info(json.dumps(log_data))

# Usage
log_json(logger,
    event="user_logged_in",
    user_id=str(user.id),
    email=user.email,
    client_ip=request.client.host
)
```

### Log Output Format

```json
{
  "timestamp": "2025-01-18T12:00:00.000Z",
  "level": "INFO",
  "event": "request_completed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status": 200,
  "duration_ms": 45.3,
  "user_id": "user-uuid"
}
```

### Request Logging Middleware

```python
# middleware/request_logging.py
class RequestLoggingMiddleware:
    async def __call__(self, request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        set_correlation_id(correlation_id)

        log_json(logger, event="request_started",
            method=request.method,
            path=request.url.path
        )

        start = time.time()
        response = await call_next(request)
        duration = (time.time() - start) * 1000

        log_json(logger, event="request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration
        )

        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

---

## Correlation IDs

### Purpose

Correlation IDs enable request tracing across services and logs.

### Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant N as Nginx
    participant B as Backend
    participant W as Worker
    participant L as Logs

    C->>N: Request
    N->>B: Request (X-Correlation-ID: abc123)
    B->>B: Set context var
    B->>L: Log {correlation_id: abc123}
    B->>W: Celery task {correlation_id: abc123}
    W->>L: Log {correlation_id: abc123}
    B-->>C: Response (X-Correlation-ID: abc123)
```

### Implementation

```python
# core/logging.py
from contextvars import ContextVar

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

def get_correlation_id() -> str:
    return correlation_id_ctx.get()

def set_correlation_id(correlation_id: str):
    correlation_id_ctx.set(correlation_id)
```

---

## Observability

### Metrics Stack

```
Backend ─────▶ /metrics ─────▶ Prometheus ─────▶ Grafana
   │                              │
   │                              │
   ▼                              ▼
Counters                     Time Series DB
Histograms                   Alert Rules
Gauges                       Dashboards
```

### Key Metrics

#### HTTP Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| http_requests_total | Counter | method, path, status | Total requests |
| http_request_duration_seconds | Histogram | method, path | Request latency |
| http_errors_total | Counter | method, path, status | Error count |
| http_requests_inprogress | Gauge | - | In-flight requests |

#### Auth Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| auth_operations_total | Counter | operation, status | Auth operations |
| auth_operation_duration_seconds | Histogram | operation | Auth latency |
| active_sessions | Gauge | - | Active refresh tokens |

#### Database Metrics

| Metric | Type | Description |
|--------|------|-------------|
| database_query_duration_seconds | Histogram | Query latency |
| database_connections | Gauge | Active connections |
| database_errors_total | Counter | Query errors |

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml
scrape_configs:
  - job_name: "tequipy-backend"
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
    scrape_interval: 15s
```

### Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: backend
    rules:
      - alert: BackendInstanceDown
        expr: up{job="tequipy-backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Backend instance is down"

      - alert: BackendHighErrorRate
        expr: |
          sum(rate(http_errors_total[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Error rate exceeds 5%"
```

---

## Security Headers

### Nginx Headers

```nginx
# X-Frame-Options - Prevent clickjacking
add_header X-Frame-Options "DENY" always;

# X-Content-Type-Options - Prevent MIME sniffing
add_header X-Content-Type-Options "nosniff" always;

# Strict-Transport-Security - Force HTTPS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# Referrer-Policy - Control referrer information
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### Backend Headers

```python
# middleware/security_headers.py
class SecurityHeadersMiddleware:
    async def __call__(self, request, call_next):
        response = await call_next(request)

        # CSP for JSON API
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"

        return response
```

### Frontend Headers (Next.js)

```typescript
// next.config.ts
headers: async () => [{
  source: "/(.*)",
  headers: [
    { key: "X-Frame-Options", value: "DENY" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    {
      key: "Content-Security-Policy",
      value: "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
    }
  ]
}]
```

---

## Configuration Management

### Environment Variables

```bash
# Backend (.env)
DEBUG=false
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
JWT_SECRET_KEY=${SECRET_FROM_VAULT}
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
RATE_LIMIT_PER_MINUTE=100
CORS_ORIGINS=["https://app.example.com"]

# Frontend (.env)
NEXT_PUBLIC_API_URL=https://api.example.com
```

### Configuration Loading

```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    debug: bool = False
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    rate_limit_per_minute: int = 100
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Middleware Chain

### Request Processing Order

```
Request
    │
    ▼
┌─────────────────────────┐
│  RequestLoggingMiddleware │  ← Generate correlation ID, log start
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│    MetricsMiddleware    │  ← Record request metrics
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│   RateLimitMiddleware   │  ← Check rate limits
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ SecurityHeadersMiddleware│  ← Add security headers
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│     CORSMiddleware      │  ← Handle CORS preflight
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│    Router Handler       │  ← Route to endpoint
└─────────────────────────┘
    │
    ▼
Response
```

### Middleware Registration

```python
# api/app.py
def create_app() -> FastAPI:
    app = FastAPI()

    # Order matters - last added runs first
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware, redis=redis_client)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
```

---

## Dependency Injection

### FastAPI Dependencies

```python
# infrastructure/dependencies.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

def get_user_repository(
    db: AsyncSession = Depends(get_db)
) -> UserRepository:
    return UserRepositoryImpl(db)

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    metrics: MetricsProvider = Depends(get_metrics_provider),
    rate_limiter: AuthRateLimiter = Depends(get_rate_limiter),
) -> AuthService:
    return AuthService(
        user_repository=user_repo,
        refresh_token_repository=token_repo,
        metrics=metrics,
        rate_limiter=rate_limiter,
    )
```

### Dependency Graph

```
get_auth_service()
├── get_user_repository()
│   └── get_db() → AsyncSession
├── get_refresh_token_repository()
│   └── get_db() → AsyncSession
├── get_metrics_provider() → PrometheusMetricsProvider
└── get_rate_limiter() → AuthRateLimiter (singleton)
```

---

## Testing Patterns

### Backend Testing

```python
# Fixture for test database
@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

# Fixture for test client
@pytest.fixture
def client(db_session):
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

# Unit test
async def test_register_user(db_session):
    repo = UserRepositoryImpl(db_session)
    service = AuthService(repo, ...)

    user = await service.register(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )

    assert user.email == "test@example.com"

# Integration test
def test_login_endpoint(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Frontend Testing

```typescript
// E2E test with Playwright
test("user can login", async ({ page }) => {
  await page.goto("/login");
  await page.fill('[name="email"]', "test@example.com");
  await page.fill('[name="password"]', "password123");
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL("/dashboard");
  await expect(page.locator("h1")).toContainText("Welcome");
});
```

---

## Health Checks

### Liveness vs Readiness

| Check | Purpose | Dependencies |
|-------|---------|--------------|
| /health (Liveness) | Is the process running? | None |
| /readiness (Readiness) | Can the service handle traffic? | Database, Redis |

### Implementation

```python
# api/v1/health.py
@router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/readiness")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    checks = {}

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Check Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    status = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

### Docker Health Checks

```yaml
# docker-compose.yml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```
