# Deployment Architecture

## Overview

This document describes the infrastructure, deployment model, and operational aspects of Tequipy.

## Deployment Model

### Development (Docker Compose)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEVELOPER MACHINE                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      DOCKER COMPOSE NETWORK                          │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │  Nginx   │  │ Frontend │  │ Backend  │  │  Worker  │            │   │
│  │  │  :80/443 │  │  :3000   │  │  :8000   │  │          │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │PostgreSQL│  │  Redis   │  │Prometheus│  │ Grafana  │            │   │
│  │  │  :5432   │  │  :6379   │  │  :9091   │  │  :3001   │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Volumes: postgres-data, prometheus-data, grafana-data, pgadmin_data       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Production (Recommended)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD PROVIDER                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         LOAD BALANCER                                │   │
│  │                    (AWS ALB / GCP LB / etc.)                        │   │
│  │                       SSL Termination                                │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                          │
│  ┌───────────────────────────────┼─────────────────────────────────────┐   │
│  │                        KUBERNETES / ECS                              │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │  Frontend   │  │  Frontend   │  │  Frontend   │  (Replicas)     │   │
│  │  │   Pod/Task  │  │   Pod/Task  │  │   Pod/Task  │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Backend   │  │   Backend   │  │   Backend   │  (Replicas)     │   │
│  │  │   Pod/Task  │  │   Pod/Task  │  │   Pod/Task  │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐                                   │   │
│  │  │   Worker    │  │   Worker    │  (Scalable)                      │   │
│  │  │   Pod/Task  │  │   Pod/Task  │                                   │   │
│  │  └─────────────┘  └─────────────┘                                   │   │
│  │                                                                      │   │
│  │  ┌─────────────┐                                                    │   │
│  │  │    Beat     │  (Singleton)                                       │   │
│  │  │   Pod/Task  │                                                    │   │
│  │  └─────────────┘                                                    │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      MANAGED SERVICES                                │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐        ┌─────────────────┐                    │   │
│  │  │    RDS/Cloud    │        │   ElastiCache/  │                    │   │
│  │  │    PostgreSQL   │        │   Memorystore   │                    │   │
│  │  │   (Multi-AZ)    │        │     Redis       │                    │   │
│  │  └─────────────────┘        └─────────────────┘                    │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Configuration

### Docker Images

| Service    | Base Image         | Size (approx) |
| ---------- | ------------------ | ------------- |
| Backend    | python:3.12-slim   | ~200MB        |
| Frontend   | node:22-alpine     | ~150MB        |
| Nginx      | nginx:1.27-alpine  | ~40MB         |
| PostgreSQL | postgres:16-alpine | ~80MB         |
| Redis      | redis:7-alpine     | ~30MB         |

### Resource Requirements

| Service    | CPU  | Memory | Scaling    |
| ---------- | ---- | ------ | ---------- |
| Frontend   | 0.5  | 512MB  | Horizontal |
| Backend    | 1.0  | 1GB    | Horizontal |
| Worker     | 0.5  | 512MB  | Horizontal |
| Beat       | 0.25 | 256MB  | Singleton  |
| PostgreSQL | 2.0  | 4GB    | Vertical   |
| Redis      | 0.5  | 512MB  | Vertical   |

### Environment Configuration

#### Development

```bash
# backend/.env
DEBUG=true
DATABASE_URL=postgresql://tequipy:tequipy@postgres:5432/tequipy
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=dev-secret-change-in-production
CORS_ORIGINS=["http://localhost","http://localhost:3000"]

# frontend/.env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Production

```bash
# backend/.env
DEBUG=false
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/tequipy
REDIS_URL=redis://elasticache-endpoint:6379/0
JWT_SECRET_KEY=${SECRET_FROM_VAULT}
CORS_ORIGINS=["https://app.example.com"]
ENABLE_HSTS=true

# frontend/.env
NEXT_PUBLIC_API_URL=https://api.example.com
```

## Health Checks

### Backend Endpoints

| Endpoint            | Purpose   | Check                            |
| ------------------- | --------- | -------------------------------- |
| `/api/v1/health`    | Liveness  | Returns 200 if app running       |
| `/api/v1/readiness` | Readiness | Checks DB and Redis connectivity |

### Docker Compose Health Checks

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s

postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5

redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

## Monitoring & Observability

### Metrics (Prometheus)

**Scrape Configuration** (`prometheus/prometheus.yml`)

```yaml
scrape_configs:
  - job_name: "tequipy-backend"
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
```

**Key Metrics:**

- `http_requests_total` - Request count by status code
- `http_request_duration_seconds` - Latency histogram
- `http_requests_inprogress` - In-flight requests

### Dashboards (Grafana)

Pre-configured dashboard: `grafana/dashboards/backend-overview.json`

**Panels:**

- Requests per second (by status)
- Latency (p50, p95)
- Backend CPU %
- Backend Memory

**Access:** http://localhost:3001 (admin/admin)

### Alerts (Prometheus)

Configured in `prometheus/alerts.yml`:

| Alert                 | Condition          | Severity |
| --------------------- | ------------------ | -------- |
| BackendInstanceDown   | up == 0 for 1m     | Critical |
| BackendHighErrorRate  | 5xx > 5% for 5m    | Warning  |
| BackendHighLatencyP95 | p95 > 750ms for 5m | Warning  |

### Logging

**Backend Logging:**

- Format: Structured JSON
- Fields: timestamp, level, message, correlation_id
- Output: stdout (container logs)

**Log Aggregation (Production):**

- Recommend: CloudWatch Logs, Stackdriver, or ELK stack
- Container logs collected by orchestrator

## Deployment Process

### Local Development

```bash
# Start all services
docker compose up -d --build

# View logs
docker compose logs -f backend

# Stop services
docker compose down
```

### Production Deployment

1. **Build Images**

   ```bash
   docker build -t tequipy-backend:v1.0.0 ./backend
   docker build -t tequipy-frontend:v1.0.0 ./frontend
   ```

2. **Push to Registry**

   ```bash
   docker push registry.example.com/tequipy-backend:v1.0.0
   docker push registry.example.com/tequipy-frontend:v1.0.0
   ```

3. **Run Migrations** (one-time job)

   ```bash
   kubectl run migration --image=tequipy-backend:v1.0.0 \
     --command -- uv run alembic upgrade head
   ```

4. **Deploy Services**
   ```bash
   kubectl apply -f k8s/
   # or
   aws ecs update-service --service backend --force-new-deployment
   ```

### Rolling Updates

- **Backend**: Stateless, supports rolling updates
- **Frontend**: Stateless, supports rolling updates
- **Worker**: Graceful shutdown with SIGTERM handling
- **Beat**: Singleton, drain before replacement

## Backup & Recovery

### Database Backup

```bash
# Manual backup
pg_dump -h postgres -U tequipy tequipy > backup_$(date +%Y%m%d).sql

# Automated (cron or K8s CronJob)
0 2 * * * pg_dump ... | gzip > backup.sql.gz && aws s3 cp backup.sql.gz s3://backups/
```

### Recovery Procedure

1. Stop application traffic
2. Restore database: `psql -U tequipy tequipy < backup.sql`
3. Run any pending migrations
4. Resume traffic

### Disaster Recovery

| Scenario                 | RTO   | RPO | Procedure                  |
| ------------------------ | ----- | --- | -------------------------- |
| Single container failure | 30s   | 0   | Auto-restart               |
| Single node failure      | 2min  | 0   | Reschedule to healthy node |
| Database failure         | 15min | 1h  | Restore from snapshot      |
| Region failure           | 4h    | 1h  | Failover to DR region      |

## Security Considerations

### Network Security

- Internal services not exposed externally
- Only Nginx ports (80/443) publicly accessible
- Database and Redis on private network

### Secrets Management

| Environment | Method                                    |
| ----------- | ----------------------------------------- |
| Development | `.env` files                              |
| Production  | AWS Secrets Manager / Vault / K8s Secrets |

### Container Security

- Non-root user in containers
- Read-only filesystem where possible
- Resource limits enforced
- Regular base image updates

## Scaling Guidelines

### Horizontal Scaling

| Component | Trigger                  | Action      |
| --------- | ------------------------ | ----------- |
| Frontend  | CPU > 70%                | Add replica |
| Backend   | CPU > 70% or p95 > 500ms | Add replica |
| Worker    | Queue depth > 100        | Add worker  |

### Vertical Scaling

| Component  | Trigger                        | Action           |
| ---------- | ------------------------------ | ---------------- |
| PostgreSQL | CPU > 80% or connections > 80% | Upgrade instance |
| Redis      | Memory > 80%                   | Upgrade instance |
