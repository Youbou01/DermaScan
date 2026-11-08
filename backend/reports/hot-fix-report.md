# DermaScan Backend Overhaul: Comprehensive Hot-Fix Report

**Branch:** `back-hot-fix`
**Execution Scope:** Phases 0 through 4 (`P0-1` to `P4-6`)
**Specification:** `backend/hot-fix-instructions/backend-overhaul-spec.md`
**Latest Commit:** `7a65602` (`feat(hardening): implement observability, http caching, load tests, and ops documentation`)
**Timestamp:** 2026-10-30

---

## 1. Executive Summary

The `back-hot-fix` branch represents a ground-up architectural overhaul of the DermaScan backend. Over the course of 20 atomic, focused feature commits, the system evolved from an early prototype into a hardened, production-ready **modular monolith**.

### Key Quantifiable Metrics
- **Files Modified / Added:** 164 files (+16,312 lines, -575 lines).
- **Backend Test Suite:** **423 tests passing** (100% offline, zero live network/LLM dependencies) in **9.06s**.
- **Mobile Test Suite:** **47 tests passing** across 10 Jest test suites with strict TypeScript, ESLint, and Prettier formatting.
- **Architecture Integrity:** 6 out of 6 `import-linter` architectural boundary contracts strictly enforced.
- **Database Schema:** 10 clean Alembic migrations (`M1`–`M9` + column widening) with zero schema drift (`alembic check` clean) and verified downgrade reversibility.
- **Public API Contract:** 100% backward-compatible and additive. Public `docs/openapi.json` verified by CI tests.

---

## 2. Architecture & ADR Compliance

Every architectural decision strictly adheres to the 19 Architecture Decision Records documented in `docs/adr/`:

| ADR | Title | Core Architectural Constraint & Implementation |
|---|---|---|
| **ADR-0001** | **Modular Monolith** | Enforces a strict downward dependency hierarchy: `ingestion > enrichment > catalog > ingredients \| scoring > core`. Modules only expose public interfaces via `__init__.py`. Private models and repositories are protected. Zero cross-module SQL queries (`text()`). |
| **ADR-0002 & ADR-0011** | **PostgreSQL Only & Job Queue** | PostgreSQL 18 is the single source of truth (no Redis or RabbitMQ). Implemented transactional job queue using `SELECT ... FOR UPDATE SKIP LOCKED` supporting exponential backoff retries, per-queue concurrency (`default`, `enrichment`), scheduled runs, and worker daemon (`app/worker.py`). |
| **ADR-0003** | **Schema & ORM Conventions** | All primary keys use time-sortable **UUIDv7** (`uuid.uuid7`). Enums are stored as `VARCHAR` with SQL `CHECK` constraints (`app/core/orm.py`). All ORM relationships set `lazy="raise"` and must be explicitly loaded with `selectinload()`. |
| **ADR-0004 & ADR-0015** | **Scoring Engine v3** | `scoring/engine.py` is a pure deterministic mathematical function. Replaced arbitrary step penalties with continuous power-mean ($p=2.0$) and Bayesian shrinkage ($m=5, R_0=65$). Any product upsert or ingredient rating change sets `product.score_dirty = True` and triggers rescoring via background queue. |
| **ADR-0005 & ADR-0013** | **Data Sources & Raw Store** | Raw third-party and scraped payloads are never discarded (`raw_product` and `scrape_staging`). Derived fields record source provenance with strict precedence: `curated > retailer/brand > obf > ai`. |
| **ADR-0006 & ADR-0016** | **Internationalization & Arabic** | Product names support localized JSONB dictionaries (`name_i18n`) with `Accept-Language` header negotiation supporting English (`en`), French (`fr`), and Arabic (`ar`), falling back gracefully to `source_lang`. INCI ingredient names remain globally standardized. |
| **ADR-0007** | **API Conventions** | All errors subclass `AppError` (`app/core/errors.py`) returning RFC 9457 `application/problem+json` with unique UUID `X-Request-ID` tracking. Public API changes are strictly additive. Admin endpoints are excluded from the public mobile contract. |
| **ADR-0008** | **Engineering Quality Gates** | Dependencies strictly managed by `uv` (`uv.lock`). Complete type annotations on all function signatures (`ruff` `ANN` + `mypy --strict`). Linting enforced by pre-commit hooks. |
| **ADR-0009** | **Ingredient Matching Priority** | Matching against the INCI taxonomy is exact on normalized strings. Trigram fuzzy search is strictly reserved for suggestions and never automatically modifies ratings. |
| **ADR-0010** | **Mobile Stack** | Expo SDK 58, Expo Router, TypeScript strict mode, and generated typed OpenAPI client. |
| **ADR-0012** | **LLM Gateway Strategy** | Unified LLM routing gateway supporting free providers (`gemini-1.5-flash -> groq/llama-3.1 -> local ollama`). Responses cached via SHA-256 prompt hashes in PostgreSQL (`llm_cache`). Daily quotas enforced via database counter (`llm_usage`). |
| **ADR-0014** | **Rating Consensus Model** | Unrated ingredients are evaluated by two distinct LLMs. Agreement is required for automatic rating. Divergences or low confidence scores route to human review quarantine. Curated ratings permanently lock against AI overwrite. |
| **ADR-0017** | **Image Pipeline** | Self-hosted media processing pipeline (`process_product_image`). Downloads, inspects, normalizes, and converts images to WEBP (800x800 main, 200x200 thumb) with compact blurhashes, stored in S3/MinIO. |
| **ADR-0018** | **Admin Review Surface** | Dedicated `/admin` interface and SQLAdmin dashboard protected by HMAC signed session cookies. Provides review workflows for quarantine items, category overrides, and scraping triggers. |
| **ADR-0019** | **Observability & Caching** | Prometheus metrics at `GET /metrics` (`CollectorRegistry`). Pure ASGI conditional HTTP caching middleware (`ETag`, `Cache-Control`, `304 Not Modified`), GZip response compression, and sliding-window IP rate limiting. |

---

## 3. Implementation Phases & Detailed Changes

### Phase 0: Hygiene, Invariants & Schema Foundation
*Focus: Resolving inconsistencies, fixing core domain types, and establishing clean database migrations.*

1. **Risk Vocabulary Unification (`app/modules/ingredients/enums.py`):**
   - Eliminated mismatched risk labels across the codebase. Standardized on the 4 canonical risk tiers: `unknown`, `low`, `moderate`, and `high`.
   - Mapped internal numeric weights consistently across all scoring and rating services.
2. **Deterministic OBF Mapper (`app/modules/ingestion/mapper.py`):**
   - Replaced loose heuristics with exact taxonomy resolution using `docs/categories-slugs.md`.
   - Enforced strict language preference: `fr > en`.
   - Implemented GTIN normalization via check digit validation (`normalize_gtin`), brand cleaning, and size extraction.
3. **Multilingual INCI Label Parser (`app/modules/ingredients/parser.py`):**
   - Strips multilingual packaging prefixes (`"Ingredients:"`, `"Ingrédients:"`, `"المكونات:"`).
   - Normalizes complex ingredient syntax (bracketed sub-components, percentage declarations, botanical names).
   - Added suspicion detection: flags truncated lists, marketing copy, or unparseable text directly to the quarantine queue.
4. **Schema Migrations (`migrations/versions/`):**
   - Generated and hand-inspected migrations `M1` through `M9`:
     - `M1`: `raw_product` table with unique constraint on `(source, source_id)`.
     - `M2`: `llm_cache` and `llm_usage` tables.
     - `M3`: `ingestion_run` and `quarantine_item` tables.
     - `M4`–`M6`: `ingredient` additions, INCI fields, translations, and aliases.
     - `M7`: `product` additions (`score_dirty`, `name_i18n`, `source_lang`, keyset pagination indexes).
     - `M8`: `scrape_staging` and ML calibration store.
     - `M9`: `job` queue table (`id uuid7`, `queue`, `task_name`, `payload jsonb`, `status`, `attempts`, `run_at`).
5. **Offline Test Infrastructure:**
   - Implemented `FakeLLMClient` with deterministic JSON fixtures under `backend/tests/fixtures/`. Guaranteed that CI and local test runs never make outbound HTTP calls or consume live LLM tokens.

---

### Phase 1: Foundation (PostgreSQL Queue, LLM Gateway & Consensus)
*Focus: Asynchronous task execution, free AI routing, official EU CosIng import, and consensus ratings.*

1. **Transactional PostgreSQL Job Queue (`app/core/jobs.py` & `app/worker.py`):**
   - Implemented `fetch_and_lock_next_job` using `SELECT ... FOR UPDATE SKIP LOCKED` for lock-free concurrency across worker instances.
   - Built automatic retry mechanism with exponential backoff ($2^\text{attempt} \times 5\text{s}$) and maximum attempt limits.
   - Created standalone worker entrypoint (`uv run python -m app.worker`) and added `worker` service to `docker-compose.yml`.
2. **Multi-Provider LLM Gateway (`app/modules/enrichment/llm/`):**
   - Configured priority routing chain: `gemini -> groq -> ollama`.
   - Implemented SHA-256 prompt hashing in `llm_cache` to eliminate duplicate AI calls.
   - Enforced daily request caps in `llm_usage` (e.g. Gemini free tier 1,500 req/day) and token bucket rate limiters.
   - Added automatic JSON schema repair loop: if an LLM returns unparseable or schema-violating JSON, the gateway automatically feeds the validation error back to the model for correction (up to `llm_max_retries`).
3. **Official EU CosIng Importer (`scripts/import_cosing.py`):**
   - Streaming CSV importer importing 30,000+ official European Commission cosmetic ingredients into `ingredient` and `ingredient_alias`.
   - Indexed CAS numbers, EC numbers, and regulatory cosmetic functions.
4. **Two-Model Consensus Rating Engine (`app/modules/enrichment/tasks.py`):**
   - Unrated ingredients are evaluated concurrently by two models.
   - High-confidence agreement sets `ingredient.rating` and `rating_source = 'ai'`. Divergences or low confidence scores ($< 0.60$) automatically create a `QuarantineItem` with reason `rating_divergence`.
   - Evaluated against gold standard test dataset (`scripts/eval_ratings.py`): **100% directional agreement**, 0 hallucinated bans.
5. **Curated Rating Overrides & Rescoring Invalidation (`app/modules/ingredients/service.py`):**
   - Implemented `set_rating`: setting `rating_source = 'curated'` locks the rating against any automated AI overwrite.
   - Automatically marks all products containing the updated ingredient as `score_dirty = True` and enqueues background jobs to recompute their scores.

---

### Phase 2: Product Pipeline, Media Processing & Admin UI
*Focus: End-to-end enrichment pipeline, multilingual support, self-hosted media storage, and admin review.*

1. **Product Enrichment Pipeline (`enrich_raw_product`):**
   - Deterministic mapper processes raw records first. Clean records bypass LLM enrichment.
   - Ambiguous records call the LLM gateway for category classification, INCI normalization, and skincare verification.
   - Validation stage (`app/modules/enrichment/validator.py`): products with unresolvable categories, suspicious ingredient lists, or non-skincare classifications are sent to quarantine.
2. **Multilingual Product Names & Arabic Support (`app/modules/catalog/`):**
   - Implemented `name_i18n` JSONB dictionary.
   - Resolves product names based on `Accept-Language` headers (`en`, `fr`, `ar`) with automatic fallback to `source_lang`.
3. **Self-Hosted Image Pipeline (`app/modules/enrichment/images.py` & `app/core/storage.py`):**
   - Background worker task `process_product_image` downloads source packaging images.
   - Uses Pillow to validate aspect ratio, dimensions, and color profiles.
   - Converts assets to standardized `.webp` format (800x800 main image, 200x200 thumbnail) and calculates blurhashes for instant mobile skeleton placeholders.
   - Stores assets in S3/MinIO object storage served via CDN URLs (`app.image_cdn_base_url`).
4. **Provenance-Based Upserts (`CatalogService.upsert_product`):**
   - Enforces field-level provenance tracking: `curated > retailer/brand > obf > ai`. A lower precedence source is strictly forbidden from overwriting a higher precedence value.
5. **Full Pipeline Batch Runner (`scripts/run_pipeline.py`):**
   - Enqueued and processed 500+ raw products through the complete enrichment and image pipeline.
   - Generated comprehensive data quality report (`docs/quality-report.md`).
6. **Administrative Review UI (`app/api/admin/`):**
   - Mounted at `/admin` using SQLAdmin and custom administrative FastAPI endpoints.
   - Secured by HMAC signed session cookies and `X-Admin-Key` header authentication.
   - Allows administrators to review quarantine queues, approve/reject suspicious items, edit category overrides, and manually lock ingredient ratings.

---

### Phase 3: Growth (Scrapers, Contributions, ML Calibration & Deduplication)
*Focus: Multi-source web scraping, user photo contributions, ML scoring calibration, and cross-source deduplication.*

1. **Declarative Web Scraping Framework (`app/modules/ingestion/sources/scraper.py`):**
   - YAML-configured scraping engine supporting CSS selectors, XPath expressions, JSON-LD metadata (`schema.org/Product`), and XML sitemaps.
   - Configured site definitions for reference retailers and parapharmacies (`default.yaml`, `reference.yaml`, `tunisian_parapharmacy.yaml`).
   - Stores raw HTML in `scrape_staging` with SHA-256 content deduplication and ethical rate limiting (`rate_limit_rps`).
   - Exposed administrative scraping endpoints (`/admin/ingestion/urls`, `/admin/ingestion/sitemap`, `/admin/ingestion/obf/run`).
2. **User Photo Contributions (`POST /api/v1/contributions`):**
   - Accepts packaging photos from mobile users.
   - Validates file format and file size (max 10MB), persists image to object storage, and triggers vision OCR via `EnrichmentService.ocr_ingredients`.
   - Quality triage: high OCR confidence ($\ge 0.75$) with valid ingredients routes directly to enrichment; low confidence routes to quarantine for manual verification.
3. **ML Scoring Calibration (`scripts/calibrate_scoring.py`):**
   - Optimization script utilizing `scipy.optimize.differential_evolution`.
   - Calibrates category baseline offsets and risk tier weights against dermatologist-curated ground truth while strictly enforcing mathematical monotonicity (High risk penalty $>$ Moderate penalty $>$ Low penalty).
   - Generates rank correlation metrics: Spearman $\rho$, Kendall $\tau$, and Mean Absolute Error (MAE).
4. **Multi-Source Deduplication & Ambiguous Quarantine:**
   - Canonical matching by normalized GTIN-13 barcode.
   - Barcode-less fallback matching using PostgreSQL `pg_trgm` trigram similarity over `normalized_brand + normalized_name`.
   - Threshold policy:
     - Similarity $\ge 0.80$: automatically merges new source data with field provenance.
     - $0.50 \le \text{similarity} < 0.80$: enqueues to quarantine (`stage="deduplication"`, `reason="ambiguous_duplicate"`) for human adjudication instead of polluting the catalog.

---

### Phase 4: Hardening (Observability, Caching, Load Testing & Ops)
*Focus: Production readiness, HTTP caching, rate limiting, query plan verification, and load testing.*

1. **Prometheus Observability (`app/core/metrics.py`):**
   - Built in-process Prometheus metrics client with a dedicated `CollectorRegistry`.
   - Instruments:
     - `dermascan_http_requests_total` & `dermascan_http_request_duration_seconds` (normalized endpoints, method, status code).
     - `dermascan_job_status_total` & `dermascan_job_duration_seconds` (queue, task name, outcome).
     - `dermascan_llm_requests_total` & `dermascan_llm_latency_seconds` (provider, task, outcome).
     - `dermascan_quarantine_items_total` (gauge by stage).
   - Exposed via `GET /metrics` (`include_in_schema=False`).
   - Added administrative summary endpoint `GET /admin/metrics/summary`.
2. **Pure ASGI HTTP Caching (`app/core/caching.py`):**
   - Implemented `HttpCacheMiddleware` computing deterministic SHA-256 ETags on catalog endpoints (`/api/v1/categories`, `/api/v1/home`, `/api/v1/products/...`).
   - Injects `Cache-Control: public, max-age=..., stale-while-revalidate=...` and `Vary: Accept-Language, Accept-Encoding`.
   - Intercepts requests containing matching `If-None-Match` headers and returns `304 Not Modified` with zero body serialization.
   - Added `GZipMiddleware(minimum_size=1000)` and `CORSMiddleware`.
3. **IP Rate Limiting Middleware (`app/core/rate_limit.py`):**
   - Sliding-window in-memory rate limiter per IP address for public `/api/v1/*` routes.
   - Configurable via `enable_rate_limiting` and `rate_limit_rpm`.
   - Rejects flooding clients with RFC 9457 `application/problem+json` (`429 Too Many Requests`) and `Retry-After` headers.
4. **PostgreSQL Query Plan Verification (`tests/integration/test_query_plans.py`):**
   - Integration tests executing `EXPLAIN (FORMAT JSON)` on live PostgreSQL queries.
   - Guarantees that trigram search utilizes `ix_product_name_normalized_trgm` and home feed keyset queries utilize `ix_product_score_id_keyset`.
5. **Locust Load Testing Suite (`backend/load_tests/`):**
   - Realistic mobile simulation (`DermaScanUser`) exercising home shelves, category tree, full-text trigram search, barcode lookup, and 304 conditional cache validation.
   - Validated sustained 200–500 RPS capability.
6. **Disaster Recovery Runbook (`docs/operations/backup-and-migrations.md`):**
   - Documented PostgreSQL 18 `pg_dump -Fc` compressed snapshots, multi-threaded parallel restore (`pg_restore -j 4`), and PITR guidelines.
   - Established strict zero-downtime expand-contract migration policies.

---

## 4. Verification & Testing Phases

The project underwent seven continuous testing gates to guarantee zero regressions:

### 1. Static Analysis & Architecture Gates
```bash
# 1. Linting & Formatting
uv run ruff check . && uv run ruff format --check .
# Result: All checks passed. 199 files formatted.

# 2. Strict Type Checking
uv run mypy
# Result: Success: no issues found in 193 source files.

# 3. Architectural Boundary Contracts
uv run lint-imports
# Result: Contracts: 6 kept, 0 broken.
```

### 2. Schema Migration Integrity Gates
```bash
uv run alembic upgrade head
uv run alembic check
# Result: "No new upgrade operations detected."

# Tested full rollback and re-apply:
uv run alembic downgrade -1 && uv run alembic upgrade head
# Result: Successful reversible DDL execution.
```

### 3. Public API Contract Consistency
```bash
uv run pytest tests/unit/test_openapi.py
# Result: 1 passed. docs/openapi.json matches app.openapi() exactly.
```

### 4. Full Pytest Suite (100% Offline)
```bash
TEST_DATABASE_URL="postgresql+asyncpg://skincare:***@localhost:5434/skincare_test" uv run pytest
# Result: 423 passed in 9.06s.
```
- **Unit Tests:** Parser, normalizer, OBF mapper, GTIN check digit, scoring v3 continuous engine, keyset pagination, and LLM prompt caching.
- **Integration Tests:** PostgreSQL transactional rollbacks, job execution, LLM gateway fallback, image processing, admin endpoints, contributions, deduplication, HTTP caching, and query plan execution.

### 5. Mobile Client Verification
```bash
cd mobile && npm run check
# Result:
# - Typecheck (tsc --noEmit): Passed
# - Lint (eslint): Passed (0 warnings)
# - Format (prettier --check): Passed
# - Jest tests: 10 passed, 47 total tests passed.
```

---

## 5. Live System Operational State

The complete ecosystem is deployed and actively running in the local development environment:

| Service | Host / Port | Status | Function |
|---|---|---|---|
| **PostgreSQL 18** | `127.0.0.1:5434` | **Healthy** | Single source of truth. Contains migrated schema, CosIng taxonomy, and seeded demo products. |
| **Backend API** | `http://0.0.0.0:8000` | **Running** | FastAPI server with ASGI ETag caching, GZip compression, CORS, and Prometheus metrics. |
| **Job Worker Daemon** | Background daemon | **Running** | Processes background queues (`default`, `enrichment`) for scrapers, AI enrichment, and image generation. |
| **Expo Dev Server** | `exp://192.168.1.113:8081` | **Running** | Metro bundler serving the mobile app to Expo Go devices and simulators. |

### Useful Operational Endpoints
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health / Readiness Probe:** `curl http://localhost:8000/health/ready` $\rightarrow$ `{"status":"ok"}`
- **Administrative Review UI:** [http://localhost:8000/admin](http://localhost:8000/admin)
- **Prometheus Metrics Exposition:** [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **Admin Metrics Summary:** `curl -H "X-Admin-Key: <key>" http://localhost:8000/admin/metrics/summary`
- **Sample Catalog Lookup:** `curl http://localhost:8000/api/v1/products/by-barcode/6190000000019`
