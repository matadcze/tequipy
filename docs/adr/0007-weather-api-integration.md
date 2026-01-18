# ADR-0007: Weather API Integration with Open-Meteo

## Status

Accepted

## Context

The application needs to provide real-time weather data to users. We need to integrate with an external weather API that provides current temperature and wind speed for any geographic coordinates.

Key requirements:

- Fetch current weather by latitude/longitude
- Handle upstream API failures gracefully
- Minimize latency and external API calls
- Avoid API key management complexity for the weather feature
- Production-ready with proper error handling and observability

## Decision

We will integrate with the **Open-Meteo API** for weather data, implementing:

1. **Open-Meteo as Weather Provider**
   - Free, no API key required
   - High availability and global coverage
   - Well-documented REST API
   - Returns temperature (Celsius) and wind speed (km/h)

2. **HTTP Client Configuration**
   - 1-second timeout (fail fast)
   - httpx async client with connection pooling
   - Singleton client instance via FastAPI lifespan

3. **Redis Caching Strategy**
   - Cache by coordinates (rounded to 2 decimal places)
   - 60-second TTL (weather data freshness requirement)
   - Cache-aside pattern (check cache → fetch → store)
   - Fail-open on cache errors (never block requests)

4. **Layered Architecture Integration**
   - `WeatherClient` protocol in domain layer
   - `OpenMeteoClient` implementation in infrastructure
   - `WeatherCache` for Redis operations
   - `WeatherService` orchestrating cache + client

5. **Error Handling**
   - `WeatherAPITimeoutError` for timeouts (502 response)
   - `WeatherAPIUnavailableError` for upstream failures (502 response)
   - Graceful degradation on cache failures

6. **Observability**
   - `weather_requests_total` counter (success/timeout/error)
   - `weather_cache_operations_total` counter (hit/miss/error)
   - `weather_upstream_duration_seconds` histogram

## API Design

```
GET /api/v1/weather/current?lat={latitude}&lon={longitude}

Response:
{
  "location": { "lat": 52.52, "lon": 13.41 },
  "current": {
    "temperatureC": 5.3,
    "windSpeedKmh": 12.5
  },
  "source": "open-meteo",
  "retrievedAt": "2026-01-18T10:30:00Z"
}
```

## Consequences

### Positive

- **No API key management**: Open-Meteo is free and keyless
- **Fast response times**: 60s cache reduces upstream calls by ~99%
- **Resilient**: Timeout + cache failures don't break the system
- **Observable**: Full metrics for monitoring and alerting
- **Testable**: Protocol-based design enables easy mocking
- **Extensible**: Can swap providers without changing service layer

### Negative

- **Limited data**: Only temperature and wind speed (no forecasts, humidity, etc.)
- **Rate limits**: Open-Meteo has fair-use limits (10,000 req/day free tier)
- **Cache coordination**: Rounded coordinates may serve slightly imprecise data
- **Dependency**: External service availability affects feature

### Neutral

- Cache TTL of 60s balances freshness vs. performance
- Coordinate rounding to 2 decimals (~1km precision) is acceptable

## Alternatives Considered

### Alternative 1: OpenWeatherMap API

**Pros:**

- More data (humidity, pressure, forecasts)
- Higher rate limits with paid plans

**Cons:**

- Requires API key management
- Free tier has lower limits
- More complex response parsing

**Not chosen:** Adds unnecessary complexity for our simple use case.

### Alternative 2: No Caching (Direct Proxy)

**Pros:**

- Always fresh data
- Simpler implementation

**Cons:**

- Higher latency (every request hits upstream)
- Risk of rate limiting
- No resilience during upstream outages

**Not chosen:** Unacceptable latency and reliability risk.

### Alternative 3: In-Memory Cache Only

**Pros:**

- Faster than Redis
- No external dependency

**Cons:**

- Not shared across replicas
- Lost on pod restart
- Memory pressure in multi-replica setup

**Not chosen:** Multi-replica deployment requires distributed cache.

## Implementation Details

### File Structure

```
backend/src/
├── api/v1/weather.py              # Router endpoint
├── domain/
│   ├── exceptions.py              # WeatherAPIError hierarchy
│   └── services/weather_service.py # Business logic
└── infrastructure/weather/
    ├── __init__.py
    ├── client.py                  # Open-Meteo HTTP client
    └── cache.py                   # Redis cache wrapper
```

### Configuration

```python
# core/config.py
weather_api_base: str = "https://api.open-meteo.com/v1"
weather_api_timeout_seconds: float = 1.0
weather_cache_ttl_seconds: int = 60
```

### Cache Key Format

```
weather:current:{lat:.2f}:{lon:.2f}
Example: weather:current:52.52:13.41
```

## References

- [Open-Meteo API Documentation](https://open-meteo.com/en/docs)
- [ADR-0004: HTTP Client and Caching Strategy](./0004-http-client-and-caching.md)
- [ADR-0001: Layered Architecture](./0001-layered-architecture.md)
