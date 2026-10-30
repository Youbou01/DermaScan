# ADR-0018: Admin Review Surface, Authentication, and Scraping Boundaries
- Status: Accepted
- Date: 2026-10-30

## Context
The ingestion and enrichment pipelines encounter products that fail deterministic validation (e.g. tokenizer/LLM disagreement, non-skincare items, incomplete labels) and are quarantined for review. Furthermore, expert pharmacist curation of ingredient ratings must take precedence over automated AI models.

To administer these operational workflows, the backend requires:
1. An administrative review API for managing quarantine queues, approving/rejecting items, inspecting ingestion runs, and locking curated ingredient ratings.
2. An auto-generated administrative dashboard (SQLAdmin) for human inspection of database tables.
3. Strict isolation preventing administrative routes from appearing in the client-facing mobile OpenAPI specification.
4. Clear ethical and engineering boundaries for public web scraping.

## Decision

1. **Dedicated Sub-Application Boundary (`app/api/admin/app.py`):**
   - Administrative endpoints are mounted as an independent FastAPI sub-application at `/admin` (`app.mount("/admin", admin_app)`).
   - Because FastAPI mounted ASGI applications do not pollute the parent application's route tree, the client contract in `docs/openapi.json` contains zero `/admin` endpoints.
   - The admin sub-application maintains its own isolated Swagger documentation at `/admin/docs`.

2. **Constant-Time API Authentication (`app/api/admin/auth.py`):**
   - Every REST endpoint under `/admin` requires the HTTP header `X-Admin-Key`.
   - The key is validated in constant time using `secrets.compare_digest` against `settings.admin_api_key`. Requests lacking a valid key receive immediate `401 Unauthorized` responses.

3. **Authenticated SQLAdmin Dashboard (`/admin/ui`):**
   - SQLAdmin is mounted at `/admin/ui` with session-based authentication (`AdminAuth` subclassing `AuthenticationBackend`).
   - Access requires login credentials matching `ADMIN_UI_USER` and `ADMIN_UI_PASSWORD`.
   - Model views (`QuarantineItemAdmin`, `RawProductAdmin`, `IngestionRunAdmin`, `IngredientAdmin`, `ProductAdmin`) are exposed through each module's public interface, maintaining strict modular monolith boundary rules.

4. **Curated Rating Locking:**
   - When an administrator modifies an ingredient rating via `POST /admin/ingredients/{id}/rating`, the rating is written with `rating_source = curated` and `source_ref = "admin-curated"`.
   - Downstream AI enrichment pipelines are prohibited from overwriting `curated` ratings.
   - Dependent products referencing the updated ingredient are marked `score_dirty = True` and rescoring jobs are automatically enqueued.

5. **Scraping Framework Scope and Guardrails:**
   - Web ingestion targets only publicly available HTML pages and open data formats (JSON-LD / Schema.org `Product`).
   - Scrapers must never reverse-engineer private mobile applications, bypass authentication or certificate pinning, or circumvent anti-bot protections.
   - Crawlers enforce politeness controls: host-level token-bucket rate limiting, jittered intervals, exponential backoff on 429/5xx, and rotating user-agent headers.

## Consequences
- Administrative functions and review dashboards are secure, authenticated, and decoupled from client traffic.
- The mobile application contract (`docs/openapi.json`) remains clean and exclusively client-focused.
- Human review and curated rating locks permanently safeguard data quality against automated hallucinations.
