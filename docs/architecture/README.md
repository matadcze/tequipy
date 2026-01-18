# Tequipy Architecture Documentation

This directory contains comprehensive architecture documentation for the Tequipy platform.

## Documentation Structure

```
docs/
├── architecture/
│   ├── README.md                    # This file
│   ├── 01-system-context.md         # C4 Level 1: System Context
│   ├── 02-container-architecture.md # C4 Level 2: Container Diagram
│   ├── 03-component-architecture.md # C4 Level 3: Component Diagrams
│   ├── 04-data-architecture.md      # Database schemas and data flow
│   ├── 05-security-architecture.md  # Security model and auth flows
│   └── 06-deployment-architecture.md# Infrastructure and deployment
└── adr/
    ├── README.md                    # ADR index and template
    ├── 0001-layered-architecture.md
    ├── 0002-jwt-authentication.md
    └── 0003-repository-pattern.md
```

## Quick Links

- [System Context](./01-system-context.md) - High-level system overview
- [Container Architecture](./02-container-architecture.md) - Services and containers
- [Component Architecture](./03-component-architecture.md) - Internal structure
- [Data Architecture](./04-data-architecture.md) - Database and data flows
- [Security Architecture](./05-security-architecture.md) - Auth and security
- [Deployment Architecture](./06-deployment-architecture.md) - Infrastructure
- [Architecture Decision Records](../adr/README.md) - Key decisions

## Architecture Overview

Tequipy is a full-stack web application built with:

- **Backend**: FastAPI (Python 3.12+) with async SQLAlchemy
- **Frontend**: Next.js 16 with React 19 and TypeScript
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Reverse Proxy**: Nginx with TLS termination
- **Monitoring**: Prometheus + Grafana

### Key Architectural Patterns

1. **Layered Architecture** - Clean separation between API, Domain, and Infrastructure
2. **Repository Pattern** - Abstract data access behind interfaces
3. **Dependency Injection** - FastAPI's `Depends()` for loose coupling
4. **JWT Authentication** - Stateless auth with access/refresh token rotation
5. **Event Sourcing (Audit)** - Immutable audit log of all user actions

## Diagram Notation

All diagrams use [Mermaid](https://mermaid.js.org/) syntax for version-controlled, text-based diagrams that render in GitHub/GitLab.
