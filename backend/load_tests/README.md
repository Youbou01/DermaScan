# Backend Load Testing Guide

This directory provides automated load testing using [Locust](https://locust.io/) to benchmark the Skincare backend API under concurrent traffic.

## Workload Profile
The default user scenario (`DermaScanUser`) simulates mobile client interactions:
- **Product Lookup (33%)**: GTIN-13 barcode lookups on `/api/v1/products/by-barcode/{barcode}`.
- **Product Search (28%)**: Full-text trigram queries on `/api/v1/products/search?q={query}`.
- **Home Feed (22%)**: Keyset paginated shelves on `/api/v1/home`.
- **Category Tree (11%)**: Hierarchical browsing on `/api/v1/categories`.
- **Health Checks (6%)**: Kubernetes / Load balancer liveness probes on `/health/live`.

Conditional caching with `ETag` and `If-None-Match` is verified automatically, simulating real client 304 response latency.

---

## Running Load Tests

### 1. Headless High-Throughput Mode (CLI)
Benchmark sustained 200–500 RPS without launching the browser UI:

```bash
cd backend
uv run locust -f load_tests/locustfile.py \
    --headless \
    --users 50 \
    --spawn-rate 10 \
    --run-time 1m \
    --host http://localhost:8000
```

### 2. Interactive Web UI
Launch Locust with its real-time analytics web dashboard:

```bash
cd backend
uv run locust -f load_tests/locustfile.py --host http://localhost:8000
```
Open [http://localhost:8089](http://localhost:8089) in your browser to configure users and view live RPS/latency charts.

---

## Performance Targets & Latency SLAs

| Endpoint | Target RPS | p95 Latency SLA | Plan / Optimization |
|---|---|---|---|
| `/health/live` | 1000+ | < 5ms | In-memory FastAPI handler |
| `/api/v1/categories` (304) | 800+ | < 10ms | ASGI ETag middleware |
| `/api/v1/products/by-barcode/:barcode` | 500+ | < 25ms | B-tree index on `product.barcode` |
| `/api/v1/products/search` | 300+ | < 50ms | `pg_trgm` GIN index on `name_normalized` |
| `/api/v1/home` | 400+ | < 35ms | Partial keyset index `ix_product_score_id_keyset` |
