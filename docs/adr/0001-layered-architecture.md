# ADR-0001: Layered Architecture Pattern

## Status

Accepted

## Context

We need to establish a code organization pattern for the backend that:

- Separates concerns clearly
- Enables independent testing of business logic
- Allows infrastructure components to be swapped without affecting business rules
- Provides clear boundaries for team collaboration
- Supports future growth and feature additions

The backend will handle authentication, user management, audit logging, and extensible agent/LLM capabilities.

## Decision

We adopt a **Layered Architecture** (also known as Clean Architecture / Hexagonal Architecture) with three main layers:

### Layer Structure

```
backend/src/
├── api/           # Presentation Layer (Inbound)
├── domain/        # Business Logic Layer (Core)
└── infrastructure/ # Infrastructure Layer (Outbound)
```

### Layer Responsibilities

1. **API Layer** (`src/api/`)
   - FastAPI routers and endpoints
   - Request/response schemas (Pydantic)
   - Middleware (CORS, rate limiting, logging)
   - HTTP-specific concerns only

2. **Domain Layer** (`src/domain/`)
   - Business entities (User, AuditEvent, RefreshToken)
   - Business rules and validation
   - Service classes containing business logic
   - Repository interfaces (abstract base classes)
   - Domain exceptions
   - No dependencies on frameworks or infrastructure

3. **Infrastructure Layer** (`src/infrastructure/`)
   - Repository implementations (SQLAlchemy)
   - Database models and sessions
   - External service integrations (Redis, LLM providers)
   - Authentication utilities (JWT, password hashing)
   - Dependency injection setup

### Dependency Rule

Dependencies flow inward: **API → Domain ← Infrastructure**

The domain layer has no knowledge of HTTP, databases, or external services.

## Consequences

### Positive

- **Testability**: Domain logic can be tested without databases or HTTP
- **Flexibility**: Infrastructure can be swapped (e.g., different database, cache provider)
- **Clarity**: Clear boundaries make code navigation easier
- **Maintainability**: Changes in one layer have minimal impact on others
- **Team scalability**: Different developers can work on different layers

### Negative

- **Initial complexity**: More files and indirection than a simple flat structure
- **Boilerplate**: Repository interfaces require both abstract and concrete classes
- **Learning curve**: Team must understand the pattern and maintain discipline

### Neutral

- Mapping between layers (entity ↔ model ↔ schema) requires explicit code
- Dependency injection setup needed via FastAPI's `Depends()`

## Alternatives Considered

### Alternative 1: Flat Structure

All code in a single directory with minimal separation.

**Rejected because**: Would become unmaintainable as features grow, difficult to test business logic independently.

### Alternative 2: Feature-Based Modules

Organize by feature (auth/, users/, audit/) with each containing its own routes, services, and models.

**Rejected because**: While good for microservices, leads to code duplication for shared concerns. Can be adopted later within each layer if needed.

### Alternative 3: Django-Style Apps

Separate Django-like "apps" with models, views, serializers per app.

**Rejected because**: Too coupled to framework conventions, doesn't fit FastAPI's lightweight approach.

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
