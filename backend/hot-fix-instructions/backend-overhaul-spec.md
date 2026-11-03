# DermaScan Backend Overhaul: Implementation Specification

**Audience:** an AI engineer (or a human) implementing this in the existing repository, working alone, step by step.
**Owner directives (binding for this project):**
1. Legal, ethical and moral considerations are handled by the team and are **out of scope** for this work. Do not add disclaimers, refusals or compliance steps for them. Only mention something when it changes the engineering (for example "this site blocks us").
2. **Everything must be free to run**: free LLM tiers and/or local models, free-tier or self-hosted storage. No paid API keys.
3. No ingredient-professional review. Quality is proven with the proxy evaluation in section 9, not by an expert.
4. Quality bar: the backend must look like a production system used by hundreds of thousands of people. Do not cut corners to go faster.
5. The owner has **approved**: the AI-in-the-middle approach, AI-assigned ingredient ratings, an ingredient score out of 10 (**10 = least concern**), the scoring v3 formula in section 8.5, and the phased plan in section 7.

> Scope boundary: work in `backend/` and `docs/`. Do not edit `mobile/` (the mobile team consumes the API through `docs/openapi.json`; section 10 says how to hand over contract changes). Scraping covers **public web pages and public APIs** only. Reverse-engineering private mobile-app APIs (authentication, certificate pinning) is out of scope.

---

## 0. How to work in this repository (read first)

Stack: Python 3.14, FastAPI, SQLAlchemy 2 async (asyncpg), Alembic, Pydantic v2, PostgreSQL 18, `uv` for dependencies, structlog, pytest.

**Conventions you must keep (they are enforced by tooling):**
- `uv add <pkg>` for dependencies (never `pip install`). Commit `uv.lock`.
- Type hints on every function signature (ruff `ANN` + `mypy --strict`). No `Any` leaks without a reason.
- All secrets and keys come from environment variables via `app/core/config.py` (`Settings`), and every new variable is documented in `backend/.env.example`.
- Modular monolith. Modules: `catalog`, `ingredients`, `scoring`, `ingestion` (+ the new `enrichment`). Rules enforced by `import-linter` (`uv run lint-imports`): dependencies point downward only; only a module may import its own `models`/`repository`; other modules use its public `__init__.py` (services + DTOs). New layer order: `ingestion > enrichment > catalog > ingredients | scoring > core`. Update the contracts in `pyproject.toml` when you add a module.
- Inside a module: `router -> service -> repository -> models`. No SQL in services, no logic in routers, **no raw SQL strings for normal reads/writes** (use the ORM/Core constructs).
- IDs are UUIDv7 (`uuid.uuid7`), never `uuid4`. Enums are VARCHAR + CHECK (`enum_type` + `enum_check` in `app/core/orm.py`). Relationships use `lazy="raise"`; load explicitly.
- Errors: raise subclasses of `AppError` (`app/core/errors.py`); the API returns RFC 9457 problem+json. Logging: `structlog.get_logger(__name__)` with keyword fields; never log secrets.
- Every model change has an Alembic migration (autogenerate, then **read and fix it**; extensions and data migrations are hand-written). One migration per concern. `alembic check` must pass.
- Tests: unit tests need no DB; integration tests use real PostgreSQL (`TEST_DATABASE_URL`, name must contain `test`). **CI must never call a live LLM or website**; use recorded fixtures.
- ADRs: any decision a newcomer would question gets a short ADR in `docs/adr/` (next number 0011). Section 13 lists the ones to write.

**Quality gate (run before every commit; all must pass):**
```bash
cd backend
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
uv run alembic upgrade head && uv run alembic check
TEST_DATABASE_URL=postgresql+asyncpg://USER:PASS@localhost:5432/skincare_test uv run pytest
```

**Existing code map (verified):**
`app/core/` (config, database, dependencies, enums, errors, i18n, keyset, logging, middleware, orm, pagination) ·
`app/modules/catalog/` (models, service, repository, router, home_*, category_*, search_*, miss_repository, gtin, schemas) ·
`app/modules/ingredients/` (models, parser, normalizer, matching, service, repository, schemas, `seed_data.csv`) ·
`app/modules/scoring/` (`engine.py`, `service.py`) ·
`app/modules/ingestion/` (`importer.py`, `mapper.py`, `fallback.py`, `seed_categories.py`, `data/categories.json`) ·
`scripts/` (`load_ingredient_seed.py`, `obf_spike.py`, `recompute_scores.py`, `run_obf_import.py`, `seed_*.py`) · `tests/{unit,integration}` · `docs/adr/0001..0010`.
Read ADR-0004 (scoring), ADR-0006 (i18n), ADR-0007 (API conventions), ADR-0009 (exact matching) before starting. ADR-0002 says "no task queue yet": this spec **supersedes** that (section 6.1).

---

## 1. Diagnosis: what is wrong today and why

| Observed in the app | Root cause (verified in code) | Fixed by |
|---|---|---|
| Category unavailable or wrong | `mapper.py` knows 16 OBF tags, matches by **substring** (`en:hair-gels` hits `en:gels` = cleanser) and **defaults to "moisturizer"** | P0-5, P2-1 |
| Brand not provided | Importer reads only OBF `brands`, keeps the text before the first comma, nothing else; empty stays empty | P0-5, P2-1 |
| Image missing / unprofessional | Stores OBF's single `image_url` as is; hotlinked; never validated or processed | P2-3 |
| Ingredients are random text in random languages; a whole list shown as one ingredient | Importer takes OBF `ingredients_text` (any language, may hold marketing text or several languages); parser splits only on `, ; • \|` and strips only English/French "Ingredients:" prefixes | P0-6, P2-1 |
| Vaseline shows only "aqua" | Not reproducible without the OBF record. Importer stores every parsed item, so either OBF's text is truncated/odd or the parser mangled it. **Diagnostic:** compare `product.raw_ingredients_text` with its `product_ingredient` rows | P0-9, P2-1 |
| Many ingredients "insufficient data" | `ingredients/seed_data.csv` has **~24 rows**; coverage must reach 0.70 to score | P0-4, P1-5 |
| "Insufficient data" even when ingredient concerns are correct | **Bug:** product score is computed once at import and stored; ingredient risk is read live per request; `recompute_scores.py` only selects `scoring_version` NULL or old, so new dictionary entries never rescore products | P0-3 |
| Rationale too technical | One short technical sentence per seed row; no reading-level rule | P1-5 |
| Language ambiguity (en/fr/ar) | OBF `lang`, `product_name_<lc>`, `ingredients_text_<lc>` ignored; translation tables nearly empty; aliases have no language tag | P0-5, P2-2 |
| Weak scoring | Weighted average of 3 point values + ad-hoc caps; unknown ingredients are dropped from the average | P0-2, P1-7 |

**Other defects to fix on the way:**
- `ingestion/importer.py`: raw SQL `text()` writes into tables owned by `catalog` and `ingredients` (violates module ownership), duplicated INSERT/UPDATE, `uuid.uuid4()`, `except Exception: return False` silently drops rows, `zip(..., strict=False)`.
- `ingestion/fallback.py`: **blocking** `urllib.request` (freezes the event loop if called from an async path), swallows all errors.
- `scoring/engine.py` defines its own `RiskLevel` and a second vocabulary (`ScoreBand` good/moderate/poor) bridged by `BAND_TO_CORE_RISK` in the importer. One vocabulary only: `app.core.enums.RiskLevel` (`low|moderate|high|unknown`).
- `scoring/service.py` is a logging wrapper around a constant (dead weight; remove or give it a purpose).

---

## 2. Target architecture

```
SOURCES            OBF dump/API | retailer & brand pages | INCI/ingredient sites | user photo (later)
   |
[ingestion] adapters ──> raw_product / scrape_staging   (immutable raw payload + content hash)
   |
[ingestion] deterministic mapper (keep only the fields we need, language-aware)
   |
[enrichment] LLM gateway ──> structured JSON (brand, category, name, i18n, clean INCI list, is_skincare, confidences)
   |                        cached by content hash; runs ONCE per distinct input; never on a request path
   |
validation ──low confidence / disagreement──> quarantine (review queue, admin UI)
   |
publish through catalog + ingredients PUBLIC services (provenance per field, precedence rules)
   |
[ingredients] ratings 0-10 (regulatory facts override AI) + plain-language texts EN/FR (+AR later)
   |
[scoring] pure formula v3 ──> product score, band, confidence; dirty flag + rescoring jobs
   |
[catalog] API (localized, cached) ──> mobile app
```
Principles: **AI at ingestion/curation time only; runtime stays deterministic and cheap.** Raw data is never discarded. Every derived field records where it came from and how sure we are. Every step is idempotent and re-runnable.

---

## 3. Decision register

| # | Decision |
|---|---|
| D1 | Keep OBF as one source among many; add raw store + AI enrichment pipeline between sources and the DB. |
| D2 | LLMs are **free only**: provider-agnostic gateway (section 5); local Ollama for bulk, free API tiers for quality-critical and vision work; limits live in config. |
| D3 | Ingredient identity is language-free (INCI name + optional OBF taxonomy id + CosIng id). Aliases carry a language tag. Runtime matching stays exact (ADR-0009). AI only *proposes/adjudicates* aliases at curation time. |
| D4 | Ingredient `rating` 0 to 10, **10 = least concern**; `risk_level` is derived from it by one function and enforced by a DB CHECK. |
| D5 | Regulatory facts (EU cosmetics annexes via CosIng) override AI. AI covers the long tail. Two independent model opinions give confidence. |
| D6 | Scoring v3: confidence-shrunk concern, power mean (q=3), exposure-weighted confidence, dirty-flag rescoring (section 8.5). Replaces weighted average and caps. |
| D7 | Languages: store original + `i18n` JSON generated once by AI, flagged machine-translated; INCI names are never translated; fallback chain requested -> `en`. |
| D8 | Images: collect real candidates, vision-pick, background-remove, normalize, host ourselves (S3-compatible + CDN). No AI-generated packaging. Category illustration placeholder if nothing qualifies. |
| D9 | Scraping: generic adapter (page -> text/JSON-LD -> same enrichment -> staging -> review), public pages only, controlled by an admin sub-app + SQLAdmin, protected by an API key. |
| D10 | Task queue now (Postgres-backed). Supersedes ADR-0002's "no queue". |
| D11 | ML is used to **calibrate constants** of the formula against reference scores, never to replace the formula. |
| D12 | Users can later contribute a missing product by photographing the ingredient list (vision LLM reads it into the same pipeline). |

---

## 4. Free LLM strategy (decision and rationale)

Free tiers change often (limits, models, even terms). **Do not hard-code vendors, model names or limits.** Verify current docs when implementing and keep everything in config.

**Chosen design: a routing gateway with per-task provider chains.**

| Task | Volume | Primary | Fallback / second opinion |
|---|---|---|---|
| Product enrichment (extract, classify, clean, translate) | high (tens of thousands) | **Local Ollama** (unlimited, no quota) | a free API tier on low confidence or failure |
| Ingredient rating + plain-language texts + alias adjudication | low (a few thousand, once each; batch 10 per request) | **Free Gemini API tier**, Flash-class model (strongest free quality; verify the current free model and limits) | second opinion from a *different* provider (a free Groq/Mistral/Cerebras tier or a local model) |
| Vision (image selection, label OCR) | medium | free Gemini API tier (vision) | local vision-capable Ollama model |
| Translation (names, texts) | with the above | same model that produced the text | |

Why this split: bulk product work is volume-heavy and tolerant, so it must not depend on daily quotas (use local). Ingredient ratings are few but accuracy-critical, so they use the strongest free model plus an independent second opinion. Results are cached forever, so each input is paid for (in quota) exactly once.

**Rules for the gateway (`app/modules/enrichment/llm/`):**
1. One interface: `generate_json(task, system, prompt, schema, images=None) -> LLMResult` (parsed + validated model, provider, model, usage, latency). Adapters: an **OpenAI-compatible adapter** (covers Ollama, Groq, OpenRouter, Mistral, Cerebras and Gemini's compatibility endpoint through `base_url` + key + model) and, only if needed for vision features, a native Gemini adapter. Use `httpx` (async). No vendor SDK lock-in.
2. **Structured output always**: send the JSON schema (provider `response_format`/`format` where supported), validate with Pydantic, retry up to 2 times with a "your JSON was invalid: <error>" repair prompt, then mark the item `failed` (never publish unvalidated output).
3. **Per-provider rate limiting**: token bucket for RPM/TPM plus a **persisted daily counter** (`llm_usage` table: provider, date, requests, tokens) so a restart cannot exceed a daily cap. Caps come from env/config. On HTTP 429 or cap reached, fall through the chain; if the whole chain is exhausted, the job is re-queued with delay (no failure).
4. **Cache**: `llm_cache(key = sha256(task | prompt_version | schema_version | normalized_input), provider, model, response_json, created_at)`. Cache hit = no call. Bump `prompt_version` to deliberately re-run.
5. **Batching**: rate ingredients 10 per request; enrich products individually (or 5 per request if the model handles it reliably, decided by the benchmark in P1-2).
6. `temperature=0` (or the provider's lowest) for all extraction/rating tasks.
7. **Benchmark before choosing models** (P1-2): run ~40 representative items per task on each candidate; choose by JSON-validity rate (target >= 98%), field accuracy against the proxy gold set, and latency. For Ollama, install a current 7B to 14B-class instruct model that supports JSON schema output (and a vision-capable one for images); check the Ollama library for the best current option, since names change. Ship an `ollama` service in `docker-compose.yml` (volume for models; GPU optional, CPU works but slower).
8. Keys and endpoints via env (section 12). Public product data only is sent to providers.
9. Tests use a `FakeLLMClient` and recorded JSON fixtures. A small opt-in script (`scripts/llm_smoke.py`) calls real providers manually.

---

## 5. Data model changes (Alembic migrations, in this order)

Use clear, separate migrations; add indexes for every FK and every filter column.

**M1. `raw_product`** (owned by `ingestion`): `id uuid7`, `source` (enum: `open_beauty_facts`, `scrape`, `user_photo`, `manual`), `source_id`, `url nullable`, `payload jsonb`, `content_hash char(64)`, `fetched_at`, unique `(source, source_id, content_hash)`.
**M2. `llm_cache`**, **`llm_usage`** (section 4).
**M3. `ingestion_run`** (id, source, started_at, finished_at, counters jsonb: fetched/mapped/enriched/published/quarantined/skipped_by_reason) and **`quarantine_item`** (id, raw_product_id, stage, reason, payload jsonb, status `pending|approved|rejected`, reviewed_by nullable, created_at).
**M4. `ingredient` additions:**
- `rating numeric(3,1) null` (0.0 to 10.0, 10 = least concern), `rating_confidence numeric(3,2) null` (0 to 1), `rating_source` enum `regulatory|curated|ai|unrated`, `rating_version smallint`, `rating_model text null`.
- `functions text[]` (preservative, emollient, surfactant...), `is_prohibited bool default false`, `is_restricted bool default false`, `is_allergen bool default false`, `cosing_id text null`, `cas text null`, `taxonomy_id text null` (OBF canonical id, e.g. `en:aqua`; verify format), `review_status` enum `auto|needs_review|approved`.
- CHECK `rating BETWEEN 0 AND 10`; **CHECK linking `risk_level` to `rating`**: NULL -> `unknown`; `>= 7.0` -> `low`; `>= 4.0 and < 7.0` -> `moderate`; `< 4.0` -> `high`. Only the service function `set_rating()` writes both.
- Keep the existing rule "moderate/high needs `source_ref`"; fill `source_ref` with the CosIng reference or a provenance string such as `ai:<provider>:<model>:v<prompt_version>`.
**M5. `ingredient_translation` additions:** `summary text null` (what it does, one sentence), `concern_note text null` (why it is flagged, plain language). Keep `rationale` for backward compatibility: set it equal to `concern_note` (or `summary` when the ingredient is low concern) so the current API keeps working.
**M6. `ingredient_alias` additions:** `language char(2) null`, `source` enum `seed|cosing|taxonomy|ai|manual`. Keep `normalized_alias` globally unique.
**M7. `product` additions:** `source_lang char(2) null`, `name_i18n jsonb null` (`{"en": "...", "fr": "..."}`), `brand_source`/`category_source` + `field_provenance jsonb` (field -> `{source, confidence, run_id}`), `enrichment_status` enum `pending|done|quarantined|failed`, `enrichment_version smallint`, `image_source_url text null`, `image_status` enum `none|candidate|processed|failed`, `image_quality numeric(3,2) null`, `score_is_estimated bool default false`, `score_dirty bool default true` + partial index `WHERE score_dirty`, `data_quality numeric(3,2) null` (completeness 0 to 1).
- `score_coverage` keeps its name (the mobile app uses it) but its meaning becomes the exposure-weighted confidence K of section 8.5.
- Unify enums: `product.score_band` stays `RiskLevel`.
**M8. `scrape_staging`** (section 8.9) and `calibration_reference` (section 8.11).
**M9. Procrastinate (or chosen queue) schema** (section 6.1).

---

## 6. Platform components

### 6.1 Job queue
Needed because enrichment, scraping, image work and rescoring are slow background jobs. Use a **PostgreSQL-backed queue** to avoid adding Redis. Recommended: **Procrastinate** (async, Postgres-native). **Verify it is maintained and compatible with Python 3.14 and SQLAlchemy/asyncpg before adopting**; if not, implement a minimal `job` table with `SELECT ... FOR UPDATE SKIP LOCKED`. Hide it behind `app/core/jobs.py` so it can be swapped. Required behavior: retries with backoff, per-queue concurrency, scheduled jobs (nightly rescoring, daily quota reset awareness), idempotent job handlers, a `worker` process (`uv run python -m app.worker`) and a `worker` service in `docker-compose.yml`. Write ADR-0011 superseding the "no queue" part of ADR-0002.

### 6.2 Object storage for images
S3-compatible API. Dev: **MinIO** in docker-compose. Prod: any free S3-compatible tier (Cloudflare R2, Backblaze B2, or self-hosted). Use `aioboto3` or `boto3` in a thread pool behind `app/core/storage.py` (`put_image(key, bytes) -> public_url`). Public base URL from env (`IMAGE_CDN_BASE_URL`). Keys: `products/<barcode>/<sha256[:16]>.webp`.

### 6.3 Admin surface
A separate FastAPI **sub-application mounted at `/admin`** (own `/admin/docs` Swagger, excluded from the public/mobile OpenAPI) plus **SQLAdmin** (auto-generated admin UI from the models) at `/admin/ui` for the review queue, quarantine, ingredient ratings and runs. Both authenticated: header `X-Admin-Key` for the API (constant-time compare with env `ADMIN_API_KEY`), login for the UI using env credentials. **Never ship admin endpoints open.**

### 6.4 Cross-cutting
`httpx.AsyncClient` shared via lifespan for all outbound HTTP (timeouts, retries with jitter, circuit breaker per host). Structured logs include `run_id`/`job_id`. Metrics (Prometheus client or OpenTelemetry) for: jobs by status, LLM calls by provider/outcome/latency, quota remaining, items by pipeline stage, quarantine size.

---

## 7. Phased plan with tasks

Each task: do the steps, add tests, run the quality gate, update docs, commit. **Phases are ordered by user-visible impact. Do not skip a task; do not reorder across phases without a reason.**

### PHASE 0: Hotfix (no AI needed; fixes what users see now)

**P0-1 Unify the risk vocabulary.** Delete `scoring/engine.RiskLevel` and `ScoreBand`; use `app.core.enums.RiskLevel` everywhere (engine, importer, `recompute_scores.py`, tests, ADR-0004 mapping table). Remove `BAND_TO_CORE_RISK`. *Done:* one enum in the codebase; all tests green.

**P0-2 Scoring v3 (pure function).** Implement section 8.5 in `scoring/engine.py` with a frozen `ScoringParams` dataclass (all constants in one place), input `Sequence[IngredientScoreInput(position, rating: float|None, confidence: float, is_prohibited: bool)]`, output `ScoreResult(score: int|None, band: RiskLevel, confidence: float, is_estimated: bool, version: int)`. `SCORING_VERSION = 3`. Until real ratings exist (P1-5), derive interim ratings from the stored level: low 9.0, moderate 5.5, high 2.0, unknown None, confidence 1.0 for rated and 0 for unknown. Test with the vectors in section 8.5 plus property tests (monotonicity: lowering any rating never raises the score; score in 0..100; adding an unknown never raises confidence). *Done:* vectors pass, mypy strict, ADR-0004 amended.

**P0-3 Dirty flag and rescoring.** Add `product.score_dirty` (M7 subset). Rules: set `score_dirty = true` for all products containing an ingredient whenever that ingredient's rating changes or when an alias is added that matches previously unmatched `product_ingredient` rows (re-match step: for rows with `ingredient_id IS NULL`, re-run exact matching and update). Implement `rematch_unmatched(session, batch)` and `recompute_dirty_scores(session, batch)` (select `score_dirty OR scoring_version < SCORING_VERSION`), a job for each, and CLI entries. Importer sets `score_dirty=false` after scoring. *Done:* adding a dictionary entry then running the jobs changes affected products' scores; integration test proves it (the stale-score bug).

**P0-4 Dictionary bootstrap (no AI).** Script `scripts/import_cosing.py`: download the EU **CosIng** ingredient export (EU Commission open data; locate the current CSV/Excel on the official portal, do not guess a URL), parse INCI names, functions, CAS, restriction annex flags, synonyms. Create `ingredient` rows with `rating NULL`, `rating_source=unrated`, flags set (`is_prohibited` for Annex II, `is_restricted` for III/IV/V/VI, allergen flag for the EU fragrance-allergen entries). Prohibited: `rating=0.5`, `rating_source=regulatory`. Aliases from CosIng synonyms (`source=cosing`), deduplicated by `normalize()` key (the unique constraint rejects collisions: log and skip the second). Idempotent upsert on `cosing_id`/`inci_name`. Then `scripts/ingredient_frequency.py`: from all stored `product_ingredient.raw_text`, normalize, count, and output the ranked unmatched tokens (this becomes the priority queue for P1-5). Keep and extend the existing `seed_data.csv` entries as `rating_source=curated`. *Done:* dictionary has >= 20,000 ingredients; frequency report committed as a CSV artifact path in docs (not data).

**P0-5 Mapper fix (category, brand, image, language).** Rewrite `ingestion/mapper.py` as a pure function `map_obf_record(record) -> MappedProduct` (Pydantic model):
- Category: use OBF `categories_tags` **and** `categories_hierarchy` with **exact** tag matching (no substring). Extend our category set (read `data/categories.json`; add e.g. eye care, lip care, body care, hand care, deodorant, shaving, baby care if present in data; keep slugs stable). **No default**: unknown -> `None` (the AI stage resolves it in Phase 2). Store the unmapped OBF tags in `field_provenance`/report for later mapping.
- Brand: take `brands_tags`/`brands` (verify field names on a real record), split on commas, normalize case, prefer the first non-empty; keep all as a list in the mapped model.
- Image: prefer the front image selected for the product's language (`selected_images.front` / `image_front_url`), else `image_url`; reject URLs that point to ingredients/nutrition images (OBF image keys contain `ingredients_`/`nutrition_`).
- Language: read `lang` and use `product_name_<lc>` and `ingredients_text_<lc>` in this preference order: `fr`, `en`, product `lang`, generic field. Record `source_lang`. If the chosen language is not `en`/`fr`, mark `needs_ai=True`.
*Done:* unit tests with real-shaped fixtures; no product gets a category the data does not support.

**P0-6 Parser hardening.** Extend `ingredients/parser.py` (keep its public contract, keep all existing tests passing):
- Prefixes (case/accent-insensitive): ingredients, ingrédients, ingredientes, ingredienti, zutaten, inhaltsstoffe, composition, inci, "ingredients (inci)", and the Arabic word for ingredients.
- **Language blocks:** if a prefix appears more than once, split into blocks and keep one block (preferred language, else the block that looks most like an INCI list).
- Separators: also ` - ` (spaced hyphen), ` / ` between items when the list has no commas, `.` followed by a capital letter when there are no commas, middle dots; keep commas inside brackets safe.
- Add `looks_like_ingredient_list(parsed) -> Suspicion(reasons)` flagging: any item longer than 120 characters, items containing sentence words (apply, avoid, store, warning, "keep out"), more than 40% items with digits only, fewer than 2 items from a long text, non-Latin script when `source_lang` is Latin. Suspicious lists set `needs_ai=True`.
*Done:* new test tables for each case above; the importer never publishes an item > 120 chars without `needs_ai`.

**P0-7 Replace `fallback.py`.** Async `httpx` client, 5 s timeout, 2 retries with jitter, typed result, structured errors (no bare `except`), a negative cache (store the miss in `barcode_miss` so we do not re-ask OBF for minutes), and route the fetched record through the **same raw store -> mapper -> pipeline** as the batch import (after P1-3; until then, through the mapper and the existing importer function). Make the endpoint behavior explicit: a miss that the fallback fills returns the product; otherwise 404 problem+json.

**P0-8 Importer hygiene (interim; Phase 2 replaces it).** Use ORM or Core constructs and UUIDv7, never swallow exceptions: every skipped row records a reason (`missing_code`, `invalid_gtin`, `no_name`, `no_ingredients`, `not_skincare`, `parse_failed`, ...) in an `ImportReport` that the script prints and stores in `ingestion_run`. Wrap each batch in a transaction with savepoints per row so one bad row never aborts the batch. Write through `catalog`/`ingredients` public services, not raw SQL on their tables.

**P0-9 Repair run and verification.** After P0-1..P0-8: re-import the sample/dump, run `rematch_unmatched` then `recompute_dirty_scores`. Produce a verification report (`scripts/quality_report.py`): % products with category, brand, image; % with >= 5 parsed ingredients; share of `unknown` bands; items > 120 chars; distribution of scores. **Phase 0 target:** unknown-band share among products with >= 5 parsed ingredients drops sharply (tracked, aim < 40% before AI ratings exist), zero wrong "moisturizer" defaults, zero stale scores.

### PHASE 1: Foundation

**P1-1 Job queue (6.1).** Worker, retries, scheduled jobs, tests with an in-process runner. ADR-0011.

**P1-2 `enrichment` module + LLM gateway (section 4).** Layout: `enrichment/{__init__,llm/{client,openai_compat,gemini,router,ratelimit,cache,fake}.py,prompts/,schemas.py,service.py}`. Config via `Settings` (providers list, per-task chains, caps). Add `ollama` and `minio` to `docker-compose.yml`. Add the benchmark script and run it to pick models; record the choice and results in `docs/llm-benchmark.md`. Update import-linter layers. *Done:* gateway passes unit tests with fakes (fallthrough on 429, cap persistence, cache hit, repair retry, schema validation); a manual smoke script works against at least one free provider and Ollama.

**P1-3 Raw store + OBF source adapter.** `ingestion/sources/obf.py` streams the OBF data dump (find the current dump on the OBF data page; do not hard-code a stale URL; support CSV and JSONL if offered) and the live per-barcode API, writing `raw_product` rows (idempotent by content hash). A `SourceAdapter` protocol (`discover() -> iterator`, `fetch()`, `to_raw()`) so scrapers (P3-1) plug in. *Done:* a full dump loads into `raw_product` without publishing anything.

**P1-4 Ingredient migrations (M4, M5, M6).** Implement `IngredientService.set_rating(...)` as the **only** writer of `rating` + `risk_level` + `source_ref`, marking dependent products dirty. Update seed loader and tests.

**P1-5 Ingredient intelligence pipeline.** Job `rate_ingredients(batch)` over the frequency-ranked unrated ingredients (top ~5,000 first; the rest are rated the first time they appear in a product). Per batch of 10 names, build the prompt from section 8.3. Steps per ingredient: (a) regulatory pre-rule from flags (section 8.3), (b) primary model rating, (c) second-opinion model rating, (d) consensus per section 8.3, (e) plain-language texts EN and FR, (f) alias proposals, (g) `set_rating`, mark `review_status`. Separate job `adjudicate_aliases` for unmatched frequent tokens: the model answers "is X the same ingredient as one of these candidates (from pg_trgm `suggest()`) or none?"; accepted answers become aliases (`source=ai`) after the validator in section 8.3. *Done:* >= 95% of the top-1,000 most frequent ingredient tokens in the data are matched exactly; every rated ingredient has texts in EN and FR; unrated rest is rated on demand.

**P1-6 Proxy evaluation harness (section 9).** Build the proxy gold set and `scripts/eval_ratings.py`. It runs in CI against recorded fixtures (no live LLM).

**P1-7 Scoring on real ratings.** Switch the scorer input to `ingredient.rating`/`rating_confidence`; keep interim derivation only for unrated ingredients. Rescore all (dirty flag). Amend ADR-0004 with the v3 parameter table and the vectors.

**P1-8 API contract additions** (section 10) + regenerate `docs/openapi.json` + notify the mobile team.

### PHASE 2: Product pipeline

**P2-1 Product enrichment (AI middleware).** `enrichment/service.py: enrich_product(mapped, raw) -> EnrichmentResult` with the schema and rules of section 8.2. Flow per raw product: mapper (deterministic) -> if the product is *clean* (category found, brand found, no `needs_ai`, language en/fr) the LLM is still called for `is_skincare` and ingredient normalization (cheap, cached) -> validation (section 8.2) -> publish or quarantine. Job `enrich_raw_product(raw_id)`.

**P2-2 Language fields.** Fill `source_lang`, `name_i18n` (AI translation once, flagged); API returns `name` in the requested locale with fallback to the original; ingredient names are INCI; rationale/summary per locale. Add Arabic as a *supported but optional* locale behind `SUPPORTED_LOCALES` once texts exist (adding "ar" must not break fallbacks). Alias `language` filled where known.

**P2-3 Image pipeline** (section 8.8). Job `process_product_image(product_id)`.

**P2-4 Publish via public services with provenance.** `CatalogService.upsert_product(...)` (new, public) accepts a `ProductUpsert` DTO with per-field provenance; precedence **curated > retailer/brand source > OBF > AI-guess**; a lower-precedence source never overwrites a higher one. Writes `product_ingredient` rows (all parsed items, unmatched kept with `ingredient_id NULL`), marks `score_dirty`. Delete the old importer once the pipeline reaches parity.

**P2-5 Full re-run.** Process all `raw_product` rows through the pipeline in the queue with the quota-aware workers. Dashboard/report of stage counters. *Targets:* >= 95% of published products have category and brand or a recorded reason; 0 published items > 120 chars; >= 85% of published products have an `en` or `fr` name and clean ingredient list; < 15% unknown band among products with >= 5 parsed ingredients; AI JSON validity >= 98%.

**P2-6 Admin review UI** (6.3): quarantine list with approve/reject/edit, ingredient rating overrides (setting `rating_source=curated` locks it from AI overwrite), run history.

### PHASE 3: Growth

**P3-1 Scraping framework + endpoint** (section 8.9).
**P3-2 Photo contribution** (section 8.10).
**P3-3 ML calibration** (section 8.11).
**P3-4 Cross-source dedupe/merge.** Barcode (GTIN-13) is canonical. For records without barcodes, match by normalized brand + name + size with a trigram threshold, and **queue ambiguous matches for review** instead of merging automatically.

### PHASE 4: Hardening

**P4-1 Observability** (metrics, error tracking, job dashboards, alerts on quota exhaustion and quarantine growth). **P4-2** HTTP caching (ETag/`Cache-Control` for product detail and home), response compression, DB indexes verified with `EXPLAIN` on search and home queries. **P4-3** Load test (Locust/k6) at several hundred requests per second on product detail and search; fix findings. **P4-4** Backups and migration policy (documented restore test). **P4-5** Security pass: admin auth, input limits, rate limiting of public endpoints (reverse proxy or middleware), dependency audit. **P4-6** Docs: update `backend/README.md`, `CONTRIBUTING.md`, ADRs.

---

## 8. Detailed specifications

### 8.1 OBF mapper: keep / drop (the "mou9arna")
Verify every field name against a real JSON record from OBF before coding (field names below are the expected ones).

| OBF field | Our field | Notes |
|---|---|---|
| `code` | `product.barcode` (via `normalize_gtin`) and `source_id` | invalid GTIN -> skip with reason |
| `lang`, `product_name`, `product_name_<lc>` | `source_lang`, `name`, `name_i18n` | language preference order in P0-5 |
| `brands`, `brands_tags` | `brand` | first non-empty, normalized |
| `categories_tags`, `categories_hierarchy` | `primary_category` | exact mapping; unknown -> AI (P2-1) |
| `ingredients_text_<lc>`, `ingredients_text` | `raw_ingredients_text` | language-selected |
| `ingredients` (OBF's parsed array: `id`, `text`, optional percent estimate), `ingredients_tags` | cross-check list + `taxonomy_id` for aliases; percent estimate used as exposure weight when present and plausible | |
| `selected_images`, `image_front_url`, `image_url`, `images` | image candidates | P2-3 |
| `quantity`, `countries_tags`, `completeness` | `size`, availability hints, `data_quality` input | |
| everything else (nutriments, nova, eco-score, packaging, ...) | **drop** | do not store beyond `raw_product.payload` |

### 8.2 Product enrichment contract
Input to the LLM: the mapped record (not the whole payload) + our category slugs with English names + the supported locales. Output (Pydantic-validated JSON):
```
{
  "is_skincare": bool, "is_skincare_confidence": 0-1,
  "brand": str|null, "brand_confidence": 0-1,
  "name_clean": str, "name_i18n": {"en": str, "fr": str},
  "source_lang": "en|fr|ar|other",
  "category_slug": one of ours | null, "category_confidence": 0-1,
  "ingredients_inci": [ {"original": str, "inci": str|null} ... ]  # label order, English INCI, junk removed
  "ingredients_confidence": 0-1,
  "flags": [ "marketing_text_removed", "multi_language_label", "truncated", "no_ingredients", ... ]
}
```
Prompt rules: never invent a brand or category (null when unsure); keep ingredient order; one entry per ingredient; remove claims, warnings and usage text; if the text contains several languages keep one complete list (prefer the one matching `source_lang`); output INCI names in English where you are certain, else `inci: null` and keep the original; no commentary.
**Validation (deterministic, after the LLM):** schema valid; `ingredients_inci` length between 2 and 120 and no item > 120 chars; the LLM list and the parser list overlap (token Jaccard on normalized names) >= 0.5, otherwise quarantine with reason `parser_llm_disagree`; `is_skincare` false -> skip with reason `not_skincare`; any confidence < threshold (default 0.6, configurable) on a field -> that field is null (and category/brand go to quarantine only if the product is otherwise valuable, i.e. completeness high). A product is publishable with null brand/category; it is **not** publishable without >= 2 clean ingredients.

### 8.3 Ingredient rating contract and rules
Input per ingredient (batch of 10): INCI name, known aliases, CosIng functions, regulatory flags (prohibited, restricted annex, allergen). Output per ingredient:
```
{ "inci": str, "rating": 0.0-10.0, "confidence": 0-1,
  "functions": [str], "key_concerns": ["irritant"|"allergen"|"comedogenic"|"endocrine_concern"|"sensitizer"|"penetration_enhancer"|"none"|...],
  "evidence": "regulatory|well_established|limited|unclear",
  "summary": {"en": str, "fr": str},          # what it does, <= 20 words, grade-6 reading level
  "concern_note": {"en": str, "fr": str}|null,   # only when rating < 7; why, <= 30 words, plain words, no jargon
  "aliases": [{"name": str, "language": "en|fr|ar|null"}] }  # synonyms, E-numbers, common names
```
Rating guide given in the prompt: 9-10 water, glycerin, well-established benign; 7-8.9 low concern, generally well tolerated; 4-6.9 moderate (known irritant/sensitizer at common use, contested evidence, restricted); below 4 high (prohibited, strong sensitizer/irritant, high-concern evidence).
**Plain-language rules (validated in code):** no sentence over 30 words; banned jargon list (e.g. "sensitization potential", "lipophilic", "occlusive agent" are rewritten as plain words); reading level check (average word length and sentence length heuristics); never use the words *safe, unsafe, toxic, harmful, dangerous* (the app's wording rule); FR text must be real French (language-detect with `langdetect`/`lingua`), not English.
**Pipeline per ingredient:**
1. **Regulatory pre-rule:** `is_prohibited` -> rating forced to 0.5, source `regulatory`, no model call needed for the rating (still generate texts). `is_restricted` or `is_allergen` -> model rating is **capped at 8.0** (never "perfectly benign").
2. **Primary** model rating, **second-opinion** model (different provider/model family).
3. **Consensus:** if `|r1 - r2| <= 1.5` -> `rating = mean`, `confidence = min(c1, c2)`; if `1.5 < diff <= 3` -> `rating = mean`, `confidence = min(c1, c2) * 0.6`, `review_status=needs_review`; if `diff > 3` -> `rating = min(r1, r2)` (conservative), `confidence = 0.3`, `needs_review`. If only one provider is available, `confidence = c1 * 0.7`.
4. `rating_source`: `regulatory` if the pre-rule applied, `ai` otherwise; `curated` ratings are never overwritten.
5. `set_rating()` writes `rating`, derived `risk_level`, `source_ref`, marks dependent products dirty.
6. **Alias validator:** accept an AI-proposed alias only if its `normalize()` key is not already owned by another ingredient (if it is, log a conflict, never overwrite) and it passes length/character checks.
Rating -> level: `>= 7.0` low, `4.0 to < 7.0` moderate, `< 4.0` high, null unknown.

### 8.4 Plain-language texts
Store per locale in `ingredient_translation(summary, concern_note)` and mirror into `rationale` (section 5, M5). API picks the locale with fallback to `en`. Arabic: generate the same two texts when `ar` is enabled; no schema change.

### 8.5 Scoring v3 (approved)
Per ingredient at label position `p` (1-based) with `rating r` (0..10) and `confidence c` (0..1):
- Concern `d = 1 - r/10`. Unrated: `r = None`, `c = 0`.
- **Weight** `w = max(0.05, 0.85^(p-1))`. If OBF supplies a plausible estimated percentage for every ingredient, use the normalized percentage as `w` instead.
- **Shrink toward a prior** (`d_prior = 0.4`): `d* = c*d + (1-c)*d_prior`. Unknown ingredients count as moderately worrying instead of disappearing.
- **Power mean** (`q = 3`, emphasizes the worst): `C = ( sum(w * d*^q) / sum(w) )^(1/q)`.
- **Score** = `round(100 * (1 - C))`, clamped 0..100. If any ingredient `is_prohibited`: `score = min(score, 25)`.
- **Confidence** `K = sum(w*c) / sum(w)` (exposure-weighted coverage; an unknown ingredient at position 1 costs far more than at position 25). Store as `score_coverage`.
- **Insufficient data** if `K < 0.35` or fewer than 3 parsed ingredients: `score = NULL`, band `unknown`. **Estimated** (`score_is_estimated = true`) if `K < 0.6`.
- **Band:** `>= 75` low, `50 to 74` moderate, `< 50` high (to be calibrated, P3-3). Prohibited ingredient forces band `high`.
- `SCORING_VERSION = 3`; every constant lives in `ScoringParams`.

**Test vectors** (rating 9.5 = benign, 2.0 = high concern, 5.0 = moderate, all confidence 1.0 unless stated; unknown = unrated). Tolerance: score exactly equal (they were computed with this exact formula).

| Case | Score | K | Insufficient | Estimated |
|---|---|---|---|---|
| 20 benign | 95 | 1.000 | no | no |
| 19 benign + 1 high at position 8 | 70 | 1.000 | no | no |
| 1 high at position 1 + 19 benign | 57 | 1.000 | no | no |
| 19 benign + 1 high at position 20 | 84 | 1.000 | no | no |
| 10 unknown | 60 (but NULL stored) | 0.000 | **yes** | yes |
| 6 benign + 4 unknown (last) | 76 | 0.776 | no | no |
| unknown at position 1 + 9 benign | 77 | 0.813 | no | no |
| 5 moderate + 15 benign | 58 | 1.000 | no | no |
| 2 benign only | (NULL stored) | 1.000 | **yes** (n < 3) | no |
| 10 benign with confidence 0.5 | 77 | 0.500 | no | **yes** |

**Invalidation:** any change to an ingredient's rating, to ingredient flags, or to alias matching marks dependent products `score_dirty`; the `recompute_dirty_scores` job (scheduled, plus triggered after rating jobs) rescores them in batches of 500. A version bump marks everything stale.

### 8.6 Language design
- Identity: INCI name (+ `taxonomy_id`, `cosing_id`). Aliases carry `language`.
- Product: `name` (original), `source_lang`, `name_i18n`. API `name` = `name_i18n[locale]` -> original. Translations are produced once by the gateway and stamped `machine_translated` inside `field_provenance`.
- Locale negotiation stays `Accept-Language` -> `core/i18n.py`. Adding `ar`: add to `SUPPORTED_LOCALES`, generate texts, test fallbacks (`ar` -> `en`).

### 8.7 Category mapping
Source of truth: our `categories.json` slugs. Deterministic exact-tag map first (P0-5); the LLM chooses a slug only from our list or null (P2-1). Log every unmapped OBF tag with its frequency (`quality_report`) so the exact map grows over time and the LLM is needed less.

### 8.8 Image pipeline (job `process_product_image`)
1. **Candidates:** OBF front image(s) (all language variants), plus images from scraped retailer/brand pages when available.
2. **Cheap filters first** (Pillow): reject short side < 500 px, aspect ratio outside 0.5 to 2.0, nearly empty/solid images.
3. **Vision classification** (free vision model, one call per candidate, cached): `front_of_pack | back | ingredients | nutrition | other`, plus `quality 0-1` (sharp, readable, whole product, no hands/shelves) and `matches_product_name: bool`. Keep the best `front_of_pack` with quality >= 0.6.
4. **Standardize:** background removal (`rembg`, local ONNX, free), trim, center on a white square canvas with padding, resize to 1024x1024, export **WebP** (and a 320 px thumbnail).
5. **Store** via `app/core/storage.py`, set `image_url` to our CDN URL, `image_source_url` to the origin, `image_quality`, `image_status=processed`. **Never hotlink** third-party images.
6. If no candidate qualifies: `image_status=none`; the API returns `image_url: null` and the app shows its placeholder (a category illustration). **Do not generate product images.**

### 8.9 Scraping framework (public web pages only)
- `ingestion/sources/` adapters implement `SourceAdapter`; a **generic page adapter** does: fetch (`httpx`; Playwright only for JS-rendered sites, optional dependency) -> extract in order: JSON-LD/`schema.org` Product (`extruct`) -> site-specific CSS selectors from a per-site YAML config -> readable text fallback -> the same LLM enrichment prompt (8.2) extracts barcode, name, brand, ingredients, images.
- Per-site config (YAML in `ingestion/sources/sites/`): base URL, sitemap/listing patterns, selectors, rate limit, concurrency, headers, optional proxy list (env), `respect_robots` (default `false` per owner decision).
- Politeness knobs (configurable): requests/second per host with jitter, retry/backoff on 429/5xx, rotating user agents, resumable crawl state in `scrape_staging` (url, status, content hash, extracted JSON, run_id).
- **Priority sources (build in this order, verify each site's structure first):** (1) brand and retailer pages exposing structured product data with barcodes and INCI lists; (2) ingredient/product reference sites that publish INCI lists and photos; (3) Tunisian parapharmacy e-shops (barcode prefix 619 is under-represented in OBF); (4) any other public skincare catalog found by search. Rank by yield (products with barcode + ingredients per hour).
- **Admin endpoints** (sub-app, `X-Admin-Key`): `POST /admin/ingestion/urls` (list of product URLs), `POST /admin/ingestion/sitemap` (site + sitemap URL), `POST /admin/ingestion/obf/run` (dump or barcode list), `GET /admin/ingestion/runs`, `GET /admin/review/quarantine`, `POST /admin/review/{id}/approve|reject`. Everything feeds the same raw store and pipeline.

### 8.10 Photo contribution (later)
`POST /api/v1/contributions` (barcode + photo of the ingredient list; multipart, size/type limits, rate limited) -> store the photo -> vision model reads the list -> `raw_product(source=user_photo)` -> same enrichment/quarantine path. Auto-publish only when confidence is high and the barcode is valid; otherwise quarantine. Returns an id the app can poll.

### 8.11 ML calibration (Phase 3, optional, after data exists)
- Collect reference scores from public sources into `calibration_reference(product_id/barcode, reference_score 0-100, source, collected_at)`. Target >= 1,000 products with full ingredient lists.
- `scripts/calibrate_scoring.py`: fit **only** the constants in `ScoringParams` (decay, floor, q, d_prior, band thresholds) by black-box optimization (e.g. `scipy.optimize.differential_evolution`) to maximize rank correlation (Spearman) with the references, on a train split; report held-out Spearman/Kendall/MAE.
- Accept new parameters only if held-out correlation improves, monotonicity tests (section 8.5 properties) still pass, and the vector table is updated deliberately. Bump `SCORING_VERSION` and write the result in ADR-0004. The formula's structure stays explainable; never replace it with a black-box model.

### 8.12 Rescoring and rematching jobs
`rematch_unmatched` (re-run exact matching for `ingredient_id IS NULL` rows, e.g. after new aliases), `recompute_dirty_scores`, `process_product_image`, `enrich_raw_product`, `rate_ingredients`, `adjudicate_aliases`, `scrape_url`. All idempotent, resumable, batch-limited, quota-aware.

---

## 9. Testing and evaluation (no expert needed)

- **Unit tests:** parser tables (all new cases), mapper fixtures, scoring vectors + property tests, rating-to-level function, consensus rules, plain-language validator, alias validator, gateway behavior with fakes.
- **Integration tests (real PostgreSQL):** dirty-flag propagation (the stale-score bug), rematch after alias insert, upsert precedence, quarantine flow, CHECK constraints (`rating` <-> `risk_level`), importer/pipeline end-to-end on a fixture OBF record set (including a multi-language label, a marketing-text label, and a "Vaseline-like" record), admin auth.
- **No live LLM or website in CI.** Record real provider responses once into `tests/fixtures/llm/*.json` and replay.
- **Proxy gold set (replaces expert review).** Build `tests/fixtures/ratings_gold.csv` (~150 ingredients) from objective sources, no human opinion needed:
  - *Expected high*: Annex II prohibited substances (from CosIng).
  - *Expected moderate-or-high*: Annex III-VI restricted and the EU fragrance-allergen entries.
  - *Expected low*: universally benign basics (water, glycerin, common emollients/humectants, tocopherol, etc.).
  - Metrics (`scripts/eval_ratings.py`): level agreement with the expected class, **inter-model agreement** (|r1 - r2| distribution), plain-language validator pass rate, JSON validity rate. Targets: >= 90% level agreement on the gold set, >= 98% JSON validity, >= 95% plain-language pass, < 15% of ingredients flagged `needs_review`.
- **Known limitation (record it in ADR-0004):** AI-assigned ratings for non-regulated ingredients are not expert-verified; the system exposes this through `rating_source`, `rating_confidence`, `review_status` and the estimated flag, and ratings can be corrected through the admin UI (`curated`).

---

## 10. API contract changes (additive, backward compatible)

The mobile app consumes `docs/openapi.json` (regenerate with `uv run python scripts/export_openapi.py`; if the script is missing in the repo, create it: build the app with dummy settings, dump `app.openapi()` with sorted keys, and add a unit test that fails when the committed file is stale). New nullable/additive fields only:
- `ProductIngredientOut`: `rating: float|null` (0-10, 10 = least concern), `summary: str|null`, `confidence: float|null`. Keep `rationale` populated (plain-language concern note).
- `ProductDetail` and `ProductCardOut`: `score_is_estimated: bool`; `score_coverage` keeps its name (now exposure-weighted confidence); `image_url` now our CDN URL or null; `name` localized with fallback.
- Keep HomeSection typed as the existing discriminated union; keep problem+json types.
Rules: never rename or remove a field; announce additions in the PR ("mobile: regenerate types"). Admin endpoints are **not** in this schema.

---

## 11. Rollout order and safety
1. Phase 0 changes ship first (they are low-risk and fix visible bugs).
2. Run migrations on a copy of the data first; every migration has a working `downgrade`.
3. Run expensive AI jobs in the queue with small batches first (100 items), inspect the quality report, then scale.
4. Keep the old importer until the pipeline reaches parity (P2-5 targets), then delete it.
5. Never overwrite `curated` data. Never delete `raw_product`.

---

## 12. Environment variables to add (document all in `.env.example`)
```
# LLM gateway (all optional; configure at least one free provider and/or Ollama)
LLM_PROVIDERS=ollama,gemini,groq
LLM_CHAIN_ENRICH=ollama,gemini
LLM_CHAIN_RATE=gemini,groq,ollama
LLM_CHAIN_VISION=gemini,ollama
OLLAMA_BASE_URL=http://localhost:11434/v1      OLLAMA_MODEL=<chosen by benchmark>   OLLAMA_VISION_MODEL=<...>
GEMINI_API_KEY=            GEMINI_MODEL=<free flash-class model, verify>   GEMINI_DAILY_REQUEST_CAP=
GROQ_API_KEY=              GROQ_MODEL=<...>                                GROQ_DAILY_REQUEST_CAP=
LLM_MIN_CONFIDENCE=0.6     LLM_MAX_RETRIES=2
# Storage / CDN
S3_ENDPOINT_URL=  S3_BUCKET=  S3_ACCESS_KEY=  S3_SECRET_KEY=  IMAGE_CDN_BASE_URL=
# Admin
ADMIN_API_KEY=  ADMIN_UI_USER=  ADMIN_UI_PASSWORD=
# Scraping
SCRAPER_RESPECT_ROBOTS=false  SCRAPER_PROXY_LIST=  SCRAPER_USER_AGENTS=
```
Compose adds: `ollama`, `minio`, `worker`. Never commit real values.

## 13. ADRs to write (docs/adr/)
0011 Job queue (supersedes the "no queue" part of ADR-0002) · 0012 LLM gateway and free-provider strategy · 0013 AI enrichment pipeline and raw store · 0014 Ingredient rating model (0-10, regulatory override, consensus) · 0015 Scoring v3 (amends ADR-0004) · 0016 Language and i18n data model · 0017 Image pipeline and hosting · 0018 Scraping scope and admin surface.

## 14. Definition of done (whole project)
- All quality gates green; `alembic check` clean; import-linter contracts updated and passing.
- Phase 0 to 2 targets (sections P0-9 and P2-5) met and recorded in a `docs/quality-report.md` produced by `scripts/quality_report.py`.
- No raw SQL on tables the module does not own; no `uuid4`; no silent exception swallowing; no blocking I/O in async paths; no AI call on a request path.
- Every pipeline stage is idempotent, resumable and observable; quotas are respected across restarts.
- Mobile contract regenerated and announced; backward compatible.
- Docs and ADRs updated.

## 15. Suggested first hour (for the implementing AI)
1. Read this file, ADR-0004/0006/0007/0009, `ingestion/*`, `scoring/engine.py`, `ingredients/parser.py`.
2. Run the quality gate and record the baseline (test count, coverage).
3. Run the Vaseline diagnostic (section 1) on the local DB if data exists.
4. Start P0-1, then P0-2, then P0-3: they remove the stale-score and "insufficient data" symptoms before any AI exists.
5. Commit per task with Conventional Commits (`fix(scoring): ...`, `feat(enrichment): ...`).
