# ADR-0004: HTTP Client and Caching Strategy

## Status

Accepted

## Context

The Tequipy backend needs to make upstream HTTP calls to external services (LLM providers, third-party APIs, webhooks). We need to:

- Choose an HTTP client library that supports async operations natively
- Implement a caching strategy to reduce latency and upstream load
- Handle connection pooling, timeouts, and retries appropriately
- Maintain consistency with our async-first architecture

### Requirements

1. **Async-native**: Must integrate seamlessly with FastAPI's async request handling
2. **Type-safe**: Strong typing support for request/response handling
3. **Production-ready**: Connection pooling, timeouts, retries, and proper error handling
4. **Testable**: Easy to mock for unit and integration tests
5. **Cache flexibility**: Support both in-memory (fast, single-node) and distributed (Redis) caching

## Decision

### HTTP Client: httpx

We adopt **httpx** as our primary HTTP client for all upstream service calls.

```python
import httpx
from contextlib import asynccontextmanager

# Application-level client with connection pooling
class HTTPClientProvider:
    _client: httpx.AsyncClient | None = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=5.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                http2=True,
            )
        return cls._client

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            await cls._client.aclose()
            cls._client = None
```

**Why httpx over alternatives:**

| Feature | httpx | aiohttp | requests |
|---------|-------|---------|----------|
| Async support | Native | Native | Sync only |
| HTTP/2 | Yes | No | No |
| API compatibility | requests-like | Different API | N/A |
| Type hints | Excellent | Good | Limited |
| Connection pooling | Built-in | Built-in | Via adapters |
| Testing | Built-in mock transport | External mocks | External mocks |

### Caching: Tiered Strategy

We implement a **tiered caching strategy** using both in-memory and Redis caches:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Request Flow                              │
├─────────────────────────────────────────────────────────────────┤
│  1. Check L1 Cache (cachetools TTLCache) → Hit? Return           │
│  2. Check L2 Cache (Redis) → Hit? Populate L1, Return            │
│  3. Fetch from upstream → Populate L2 + L1, Return               │
└─────────────────────────────────────────────────────────────────┘
```

#### L1 Cache: cachetools TTLCache (In-Memory)

For frequently accessed, latency-sensitive data:

```python
from cachetools import TTLCache
from cachetools.keys import hashkey
import asyncio

class InMemoryCache:
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._cache[key] = value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)
```

**Use cases:**
- Configuration lookups
- User session data
- Rate limit counters (local fallback)
- Frequently accessed reference data

#### L2 Cache: Redis (Distributed)

For shared state across multiple backend instances:

```python
from redis.asyncio import Redis
import json

class RedisCache:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self.redis.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)
```

**Use cases:**
- LLM response caching (expensive operations)
- Cross-instance rate limiting
- Session data in multi-replica deployments
- Distributed locks

#### Cache Decorator Pattern

```python
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def cached(
    ttl: int = 300,
    key_prefix: str = "",
    use_redis: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cache_key = f"{key_prefix}:{hashkey(*args, **kwargs)}"

            # Check L1
            cached_value = await l1_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Check L2 if enabled
            if use_redis:
                cached_value = await redis_cache.get(cache_key)
                if cached_value is not None:
                    await l1_cache.set(cache_key, cached_value)
                    return cached_value

            # Fetch and cache
            result = await func(*args, **kwargs)

            await l1_cache.set(cache_key, result)
            if use_redis:
                await redis_cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator
```

## Consequences

### Positive

- **Performance**: L1 cache provides sub-millisecond access for hot data
- **Scalability**: Redis L2 cache enables horizontal scaling with shared state
- **Consistency**: httpx's async-native design prevents thread-safety issues
- **Testability**: httpx's mock transport and cachetools' simple API enable easy testing
- **HTTP/2 support**: Multiplexed connections reduce latency to modern APIs
- **Connection reuse**: Pooled connections reduce TLS handshake overhead

### Negative

- **Memory overhead**: L1 cache consumes application memory
- **Complexity**: Two-tier caching requires careful invalidation strategy
- **Dependency**: Additional libraries (httpx, cachetools) to maintain

### Neutral

- Cache invalidation must be handled explicitly per use case
- TTL tuning required based on data freshness requirements

## Alternatives Considered

### Alternative 1: aiohttp Only

Use aiohttp for HTTP calls without httpx.

**Rejected because**: Different API from requests, no HTTP/2 support, less intuitive for developers familiar with requests.

### Alternative 2: Redis Only (No L1)

Use Redis for all caching, skip in-memory cache.

**Rejected because**: Network roundtrip for every cache check adds ~1-2ms latency, unnecessary for single-node deployments.

### Alternative 3: functools.lru_cache

Use Python's built-in LRU cache.

**Rejected because**: Not TTL-aware (stale data persists), not thread-safe for async, no size-based eviction control.

### Alternative 4: aiocache

Use aiocache library for unified caching.

**Rejected because**: Additional abstraction layer, less control over cache behavior, cachetools + redis provides sufficient flexibility.

## Implementation Guidelines

### Timeout Configuration

```python
# Default timeouts (can be overridden per-request)
TIMEOUT_CONFIG = {
    "default": httpx.Timeout(30.0, connect=5.0),
    "llm_provider": httpx.Timeout(120.0, connect=10.0),  # LLM calls can be slow
    "health_check": httpx.Timeout(5.0, connect=2.0),     # Fast fail for health
}
```

### Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def fetch_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.get(url)
    response.raise_for_status()
    return response
```

### Cache Key Strategy

```python
# Consistent key generation
def make_cache_key(prefix: str, *args, **kwargs) -> str:
    import hashlib
    import json

    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    hash_suffix = hashlib.sha256(key_data.encode()).hexdigest()[:16]
    return f"{prefix}:{hash_suffix}"
```

## References

- [httpx documentation](https://www.python-httpx.org/)
- [cachetools documentation](https://cachetools.readthedocs.io/)
- [Redis async Python client](https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html)
- [ADR-0001: Layered Architecture](./0001-layered-architecture.md)
