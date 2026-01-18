# ADR-0006: Frontend API Client Design

## Status

Accepted

## Context

The frontend needs to communicate with the FastAPI backend for:

- Authentication (login, register, token refresh)
- User profile management
- Audit log retrieval
- Agent/LLM interactions

We need an API communication layer that:

- Is type-safe with TypeScript
- Handles JWT token management transparently
- Provides consistent error handling
- Supports request timeouts and cancellation
- Is easy to use and extend

## Decision

We implement a **Singleton API Client** pattern with method grouping:

### Architecture

```typescript
// lib/api/client.ts
class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;

  // Token Management
  setAccessToken(token: string | null): void;
  getAccessToken(): string | null;

  // Core Request Method
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T>;

  // Grouped API Methods
  readonly auth = {
    register: (data) => this.post<UserResponse>("/auth/register", data),
    login: (data) => this.post<TokenResponse>("/auth/login", data),
    logout: () => {
      this.setAccessToken(null);
    },
    refreshToken: (data) => this.post<TokenResponse>("/auth/refresh", data),
    me: () => this.get<UserResponse>("/auth/me"),
    // ... other auth methods
  };

  readonly audit = {
    list: (params) => this.get<AuditEventListResponse>("/audit", { params }),
  };

  readonly agents = {
    run: (data) => this.post<AgentRunResponse>("/agents/run", data),
  };
}

export const apiClient = new ApiClient();
```

### Key Design Decisions

1. **Singleton Pattern**
   - Single instance shared across the application
   - Token state persisted between calls
   - Consistent configuration

2. **Method Grouping**
   - Methods organized by feature domain
   - Clear API surface: `apiClient.auth.login()`, `apiClient.audit.list()`
   - Easy to discover available operations

3. **Generic Request Method**
   - Type-safe responses via generics
   - Centralized error handling
   - Automatic token injection

4. **Token Storage in localStorage**
   - Persists across page refreshes
   - Accessible from any component
   - Simple implementation

5. **Custom Error Class**
   ```typescript
   class ApiError extends Error {
     constructor(
       message: string,
       public status: number,
       public response?: ErrorResponse,
       public correlationId?: string,
     ) {
       super(message);
     }
   }
   ```

### Error Handling Pattern

```typescript
// In API client
private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(this.accessToken && { Authorization: `Bearer ${this.accessToken}` }),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      error?.error?.message || "Request failed",
      response.status,
      error,
      response.headers.get("x-correlation-id") || undefined
    );
  }

  return response.json();
}

// In components
try {
  const user = await apiClient.auth.login({ email, password });
} catch (error) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      setError("Invalid credentials");
    } else if (error.status === 429) {
      setError("Too many attempts. Please wait.");
    }
  }
}
```

### Integration with Context

```typescript
// contexts/AuthContext.tsx
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);

  const login = async (email: string, password: string) => {
    const { access_token } = await apiClient.auth.login({ email, password });
    apiClient.setAccessToken(access_token);
    const user = await apiClient.auth.me();
    setUser(user);
  };

  // ... other methods
}
```

## Consequences

### Positive

- **Type Safety**: Full TypeScript support for requests/responses
- **Simplicity**: No external dependencies (fetch only)
- **Extensibility**: Easy to add new endpoints
- **Consistency**: Uniform error handling across the app
- **Token Management**: Automatic token injection

### Negative

- **No Caching**: Each request hits the server (acceptable for current scope)
- **No Retry Logic**: Failed requests are not automatically retried
- **localStorage Security**: Tokens accessible to XSS attacks (mitigated by CSP)
- **Manual Refresh**: Token refresh not automatic (handled by AuthContext)

### Neutral

- Requires manual type definitions for API responses
- No request deduplication (multiple calls to same endpoint run separately)
- Network errors surface as generic errors

## Alternatives Considered

### Alternative 1: axios

HTTP client with interceptors and more features.

**Rejected because**: fetch is built-in and sufficient. axios adds bundle size without significant benefit.

### Alternative 2: React Query / TanStack Query

Powerful data fetching with caching, deduplication, background refetching.

**Rejected because**: Adds complexity. Our API calls are mostly mutations or infrequent reads. May adopt later if needed.

### Alternative 3: tRPC

End-to-end type safety without manual type definitions.

**Rejected because**: Requires backend changes (FastAPI adapters). Significant migration effort.

### Alternative 4: GraphQL

Query-based API with Apollo Client or urql.

**Rejected because**: Would require complete backend rewrite. REST is sufficient for current needs.

### Alternative 5: httpOnly Cookies for Tokens

Store JWT in httpOnly cookies instead of localStorage.

**Rejected because**: Requires backend changes for cookie handling. Current CSP mitigates XSS risks. May implement for production.

## Implementation Notes

### Request Timeout

```typescript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);

try {
  const response = await fetch(url, { signal: controller.signal });
} finally {
  clearTimeout(timeoutId);
}
```

### Custom Hooks for API Calls

```typescript
// hooks/useApi.ts
export function useApi<T>(apiFn: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiFn();
      setData(result);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, [apiFn]);

  return { data, loading, error, execute };
}
```

## References

- [MDN Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [TypeScript Handbook - Generics](https://www.typescriptlang.org/docs/handbook/2/generics.html)
- [ADR-0005: Frontend Architecture](./0005-frontend-architecture.md)
- [ADR-0002: JWT Authentication](./0002-jwt-authentication.md)
