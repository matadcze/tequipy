# API Reference

## Overview

The Tequipy Backend exposes a RESTful API at `/api/v1/`. All endpoints return JSON responses.

**Base URL:** `http://localhost:8000/api/v1`
**OpenAPI Docs:** `http://localhost:8000/docs`
**ReDoc:** `http://localhost:8000/redoc`

## Authentication

The API uses JWT Bearer token authentication.

```http
Authorization: Bearer <access_token>
```

### Token Lifecycle

| Token         | Expiration | Purpose                 |
| ------------- | ---------- | ----------------------- |
| Access Token  | 15 minutes | API authentication      |
| Refresh Token | 7 days     | Obtain new access token |

## Response Format

### Success Response

```json
{
  "id": "uuid",
  "field": "value"
}
```

### Error Response

```json
{
  "error": {
    "code": "ErrorType",
    "message": "Human-readable message",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

### HTTP Status Codes

| Code | Meaning               |
| ---- | --------------------- |
| 200  | Success               |
| 201  | Created               |
| 204  | No Content            |
| 400  | Bad Request           |
| 401  | Unauthorized          |
| 403  | Forbidden             |
| 404  | Not Found             |
| 422  | Validation Error      |
| 429  | Rate Limited          |
| 500  | Internal Server Error |

## Rate Limiting

| Endpoint Type   | Limit        | Window   |
| --------------- | ------------ | -------- |
| General API     | 100 requests | 1 minute |
| Login           | 5 attempts   | Per IP   |
| Registration    | 3 attempts   | Per IP   |
| Token Refresh   | 10 attempts  | Per IP   |
| Password Change | 5 attempts   | Per user |

Rate limit headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

## Health Endpoints

### GET /health

Simple liveness check. Always returns 200 if the service is running.

**Authentication:** None

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-01-18T12:00:00Z"
}
```

### GET /readiness

Deep health check. Verifies database and Redis connectivity.

**Authentication:** None

**Response:**

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok"
  },
  "timestamp": "2025-01-18T12:00:00Z"
}
```

---

## Authentication Endpoints

### POST /auth/register

Create a new user account.

**Authentication:** None
**Rate Limit:** 3/min per IP

**Request:**

```json
{
  "email": "user@example.com",
  "password": "minimum8chars",
  "full_name": "John Doe"
}
```

| Field     | Type   | Required | Constraints        |
| --------- | ------ | -------- | ------------------ |
| email     | string | Yes      | Valid email format |
| password  | string | Yes      | 8-72 characters    |
| full_name | string | No       | 1-255 characters   |

**Response (201):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2025-01-18T12:00:00Z",
  "updated_at": "2025-01-18T12:00:00Z"
}
```

**Errors:**

- 400 - Email already registered
- 422 - Validation error (invalid email, password too short)

### POST /auth/login

Authenticate and receive tokens.

**Authentication:** None
**Rate Limit:** 5/min per IP

**Request:**

```json
{
  "email": "user@example.com",
  "password": "minimum8chars"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Errors:**

- 401 - Invalid credentials
- 401 - Account locked (after 5 failed attempts)
- 429 - Rate limited

### POST /auth/refresh

Exchange refresh token for new token pair.

**Authentication:** None
**Rate Limit:** 10/min per IP

**Request:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Errors:**

- 401 - Invalid or expired refresh token
- 401 - Token has been revoked

### GET /auth/me

Get current user profile.

**Authentication:** Required

**Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2025-01-18T12:00:00Z",
  "updated_at": "2025-01-18T12:00:00Z"
}
```

### PUT /auth/profile

Update user profile.

**Authentication:** Required

**Request:**

```json
{
  "full_name": "Jane Doe"
}
```

**Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "is_active": true,
  "created_at": "2025-01-18T12:00:00Z",
  "updated_at": "2025-01-18T12:00:00Z"
}
```

### POST /auth/change-password

Change user password.

**Authentication:** Required
**Rate Limit:** 5/min per user

**Request:**

```json
{
  "current_password": "currentpassword",
  "new_password": "newpassword123"
}
```

**Response (204):** No content

**Errors:**

- 400 - Current password incorrect
- 400 - New password same as current
- 422 - New password too short

**Side Effects:**

- All refresh tokens are revoked (forces re-login on all devices)

### DELETE /auth/me

Delete user account.

**Authentication:** Required

**Response (204):** No content

**Side Effects:**

- All refresh tokens deleted
- Audit events preserved with user_id = NULL

---

## Audit Endpoints

### GET /audit

List audit events for current user.

**Authentication:** Required

**Query Parameters:**

| Parameter   | Type     | Required | Default | Description               |
| ----------- | -------- | -------- | ------- | ------------------------- |
| page        | integer  | No       | 1       | Page number (1-indexed)   |
| page_size   | integer  | No       | 10      | Items per page (1-50)     |
| event_type  | string   | No       | -       | Filter by event type      |
| resource_id | uuid     | No       | -       | Filter by resource ID     |
| start_date  | datetime | No       | -       | Filter events after date  |
| end_date    | datetime | No       | -       | Filter events before date |

**Event Types:**

- USER_REGISTERED
- USER_LOGGED_IN
- USER_LOGGED_OUT
- PASSWORD_CHANGED
- USER_UPDATED
- USER_DELETED
- RESOURCE_CREATED
- RESOURCE_UPDATED
- RESOURCE_DELETED

**Response (200):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user-uuid",
      "event_type": "USER_LOGGED_IN",
      "resource_id": null,
      "details": {
        "client_ip": "192.168.1.1"
      },
      "created_at": "2025-01-18T12:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "pages": 10
}
```

---

## Agent Endpoints

### POST /agents/run

Execute an LLM agent prompt.

**Authentication:** None (currently open)

**Request:**

```json
{
  "prompt": "What is the capital of France?",
  "system": "You are a helpful assistant."
}
```

| Field  | Type   | Required | Description                   |
| ------ | ------ | -------- | ----------------------------- |
| prompt | string | Yes      | User prompt (min 1 char)      |
| system | string | No       | System guidance for the agent |

**Response (200):**

```json
{
  "output": "The capital of France is Paris.",
  "steps": [
    {
      "step_type": "thought",
      "content": "Parsing request..."
    },
    {
      "step_type": "response",
      "content": "The capital of France is Paris."
    }
  ]
}
```

**Note:** Currently uses a stub LLM provider. Production will integrate with external LLM services.

---

## Weather Endpoints

### GET /weather/current

Get current weather for geographic coordinates.

**Authentication:** None

**Query Parameters:**

| Parameter | Type  | Required | Constraints | Description          |
| --------- | ----- | -------- | ----------- | -------------------- |
| lat       | float | Yes      | -90 to 90   | Latitude coordinate  |
| lon       | float | Yes      | -180 to 180 | Longitude coordinate |

**Response (200):**

```json
{
  "location": {
    "lat": 52.52,
    "lon": 13.41
  },
  "current": {
    "temperatureC": 5.3,
    "windSpeedKmh": 12.5
  },
  "source": "open-meteo",
  "retrievedAt": "2025-01-18T12:00:00Z"
}
```

**Errors:**

- 422 - Invalid coordinates (out of range or wrong type)
- 502 - Upstream weather API unavailable or timeout

**Caching:** Results are cached for 60 seconds. Coordinates are rounded to 2 decimal places for cache key generation (~1.1km precision at equator).

**Rate Limiting:** Standard API rate limits apply (100 req/min).

---

## Metrics Endpoint

### GET /metrics

Prometheus-format metrics.

**Authentication:** None (blocked at Nginx level)

**Response:**

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api/v1/health",status="200"} 42
```

---

## Common Headers

### Request Headers

| Header           | Required | Description                                    |
| ---------------- | -------- | ---------------------------------------------- |
| Content-Type     | Yes      | application/json                               |
| Authorization    | Depends  | Bearer token for protected endpoints           |
| X-Correlation-ID | No       | Request tracing ID (auto-generated if missing) |

### Response Headers

| Header                | Description        |
| --------------------- | ------------------ |
| X-Correlation-ID      | Request tracing ID |
| X-RateLimit-Limit     | Rate limit ceiling |
| X-RateLimit-Remaining | Remaining requests |
| X-RateLimit-Reset     | Reset timestamp    |

---

## TypeScript Types

Frontend type definitions are available in frontend/src/lib/types/api.ts:

```typescript
interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface AuditEventResponse {
  id: string;
  user_id: string | null;
  event_type: EventType;
  resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    correlation_id?: string;
  };
}
```

---

## Frontend API Client Usage

```typescript
import { apiClient } from "@/lib/api/client";

// Login
const { access_token, refresh_token } = await apiClient.auth.login({
  email: "user@example.com",
  password: "minimum8chars",
});

// Get current user
const user = await apiClient.auth.me();

// List audit events
const { items, total } = await apiClient.audit.list({
  page: 1,
  page_size: 10,
  event_type: "USER_LOGGED_IN",
});

// Run agent
const { output, steps } = await apiClient.agents.run({
  prompt: "Hello, world!",
});
```
