# ADR-0019: Observability, HTTP Caching, and API Hardening

- Status: Accepted
- Date: 2026-10-30
- Related: ADR-0001, ADR-0002, ADR-0007, ADR-0011

## Context
As DermaScan moves to production, the API must handle mobile app traffic efficiently, provide deep operational observability without external SaaS dependencies, protect public endpoints against abuse, and ensure sub-50ms p95 latency on read-heavy catalog queries.

## Decisions

### 1. Prometheus-Compatible In-Process Metrics
- We adopt `prometheus-client` with a dedicated `CollectorRegistry`.
- Metrics track HTTP request rate/latency, asynchronous job executions (by queue, task, and outcome status), LLM gateway requests (by provider, task, and outcome), and quarantine queue growth.
- Metrics are exposed at `/metrics` (Prometheus exposition format), excluded from the public mobile OpenAPI schema (`include_in_schema=False`).
- An administrative JSON summary is provided at `/admin/metrics/summary`.

### 2. Pure ASGI Conditional Caching (ETag / Cache-Control)
- We implement `HttpCacheMiddleware` at the ASGI level.
- Read-heavy endpoints (`/api/v1/categories`, `/api/v1/home`, `/api/v1/products/...`) generate deterministic SHA-256 ETags and set `Cache-Control: public, max-age=...` headers.
- If the incoming request contains a matching `If-None-Match`, the middleware intercepts and immediately returns `304 Not Modified` with an empty body, avoiding downstream serialization and database load.
- Starlette `GZipMiddleware` is enabled for response payloads exceeding 1000 bytes.

### 3. IP Rate Limiting for Public Endpoints
- We implement `RateLimitMiddleware` using an in-memory sliding window algorithm per client IP on `/api/v1/*`.
- Configurable via `enable_rate_limiting` and `rate_limit_rpm`.
- Violations return RFC 9457 `application/problem+json` with status 429 and `Retry-After` header.

### 4. Database Query Plan Assurance
- Read query performance is continuously verified using PostgreSQL `EXPLAIN` integration tests (`tests/integration/test_query_plans.py`).
- Asserts usage of the `pg_trgm` GIN index for search and the keyset pagination index for score ranking.

## Consequences
- Operational visibility is complete without requiring third-party monitoring agents.
- Mobile client bandwidth and latency are drastically reduced via 304 caching.
- System stability is protected against traffic spikes and scraping bots.
