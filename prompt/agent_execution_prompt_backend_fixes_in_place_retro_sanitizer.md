# System Role & Execution Mandate (For Coding Agent: Gemini 3.8 Flash)

You are an autonomous Senior Backend Engineer working inside the `backend/` directory of the **DermaScan** repository (Python 3.14, FastAPI, SQLAlchemy 2 Async, PostgreSQL 18, `uv`).

## Strict Operating Rules
1. **Execute & Test Only What Is Specified:** Execute the Pre-Flight Checks and Micro-Steps `1` through `8` sequentially. Do **not** invent unrelated refactors, do **not** drop the database (`DROP DATABASE` / `docker compose down -v` is strictly forbidden), and do **not** touch `mobile/`.
2. **Respect Project Architecture & Quality Gates:**
   - Package manager: `uv` only (`uv run ...`).
   - Type annotations: Every function signature must have full type annotations (`ruff` `ANN` + `mypy --strict`).
   - Module boundary rules (`uv run lint-imports`):
     - Layer hierarchy: `app.main > app.api > app.modules > app.core`. **Never** import anything from `app.modules` inside `app.core`.
     - Module hierarchy: `ingestion > enrichment > catalog > ingredients | scoring`.
     - Private internals: A module's `models.py` and `repository.py` are private to that module. Cross-module calls must go through public `__init__.py` services/DTOs.
3. **Be Agile When Environment State Dictates:** Before modifying runtime configurations or running background workers, inspect the output of the Pre-Flight Checks and adapt provider chains (`ollama`, `gemini`, `groq`) based on which services/keys are actually reachable in the environment.

---

## Phase 0: Pre-Flight Checks (MUST Execute First)

Run these commands from `backend/` before making any code changes. Their output determines how you configure the LLM fallback chain and database cleanup parameters.

### Pre-Step 0.1 — Check Running Docker Containers & Services
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
- **Decision Rule:**
  - Verify that Postgres (`skincare-db-1`) and MinIO (`skincare-minio-1`) are running and healthy. If not, start them with `docker compose up -d db minio minio-init`.
  - Check if `ollama` container or local Ollama (`http://localhost:11434/v1/models`) is reachable:
    ```bash
    curl -s http://localhost:11434/v1/models || echo "Ollama not reachable"
    ```

### Pre-Step 0.2 — Inspect `.env` LLM & Storage Settings (Without Printing Secrets)
```bash
uv run python -c "
from app.core.config import get_settings
s = get_settings()
print('llm_providers:', s.llm_providers)
print('llm_chain_rate:', s.llm_chain_rate)
print('llm_chain_enrich:', s.llm_chain_enrich)
print('has_gemini_key:', bool(s.gemini_api_key))
print('has_groq_key:', bool(s.groq_api_key))
print('ollama_model:', s.ollama_model)
print('s3_endpoint_url:', s.s3_endpoint_url)
print('image_cdn_base_url:', s.image_cdn_base_url)
"
```
- **Decision Rule:**
  - If `has_groq_key` is `False` and Ollama is reachable, ensure `ollama` is present in `LLM_CHAIN_RATE` and `LLM_CHAIN_ENRICH` in `.env` so `rate_ingredients` has a working fallback when Gemini hits quota/validation errors.

### Pre-Step 0.3 — Capture Baseline Database Diagnostics
```bash
docker exec -i skincare-db-1 psql -U skincare -d skincare -c "
SELECT status, task_name, count(*) FROM job GROUP BY 1, 2 ORDER BY 3 DESC;
SELECT rating_source, risk_level, count(*) FROM ingredient GROUP BY 1, 2 ORDER BY 3 DESC;
SELECT enrichment_status, image_status, count(*) FROM product GROUP BY 1, 2 ORDER BY 3 DESC;
SELECT count(*) AS corrupted_translations FROM ingredient_translation WHERE strpos(rationale, '?') > 0 OR strpos(rationale, chr(65533)) > 0;
SELECT count(*) AS xx_brands FROM brand WHERE name ~ '^[a-zA-Z]{2}:';
"
```

---

## Micro-Step 1: Fix `LLMRouter` Error Reporting & Job Retry Handling

### Root Cause
1. In `backend/src/app/modules/enrichment/llm/router.py`, inside `LLMRouter.generate_json`:
   - When `res.parsed is None` (lines 199–207) or when `except ValidationError as err:` triggers (lines 224–234), `last_error` is **never assigned**. When `repair_attempts` exceeds `max_retries`, the loop exits with `last_error = None`, raising `LLMChainExhaustedError("All providers in chain ['gemini'] exhausted for task 'rate'. Last error: None")`.
2. In `backend/src/app/core/jobs.py`, `execute_job` treats temporary LLM rate-limit / quota exhaustion as a normal crash and permanently marks the job `FAILED` after 3 quick attempts.

### Required Changes
1. **In `backend/src/app/modules/enrichment/llm/router.py`:**
   - Import `LLMInvalidResponseError` from `app.modules.enrichment.llm.client`.
   - In `if res.parsed is None:`, assign:
     ```python
     last_error = LLMInvalidResponseError(
         f"Provider {provider} returned unparseable JSON: {res.content[:200]}"
     )
     ```
     before `continue`.
   - In `except ValidationError as err:`, assign:
     ```python
     last_error = err
     ```
     before constructing the repair prompt.
2. **In `backend/src/app/core/jobs.py`:**
   - **IMPORTANT (`lint-imports` rule):** Do **not** import from `app.modules` in `app/core/jobs.py`.
   - In `execute_job`'s `except Exception as exc:` block, detect rate-limit / chain exhaustion by checking:
     ```python
     is_rate_or_quota = type(exc).__name__ in (
         "LLMChainExhaustedError",
         "LLMRateLimitError",
         "LLMQuotaExhaustedError",
     )
     ```
   - When `is_rate_or_quota` is `True` and `db_job.attempts < max(db_job.max_attempts, 6)`:
     reschedule `db_job.status = JobStatus.PENDING` with a longer cooldown `backoff_secs = min(300, 30 * db_job.attempts)` so temporary provider rate limits do not immediately kill the job.

### Verification
```bash
uv run pytest tests/unit/test_llm_gateway_unit.py tests/integration/test_llm_gateway.py tests/integration/test_jobs.py -v
uv run lint-imports
```

---

## Micro-Step 2: Fix `rate_ingredients` Provider Chain, Empty Payload Bug, & Priority Ordering

### Root Cause
1. In `backend/src/app/modules/enrichment/service.py` (line 258):
   `rate_ingredients` sets `primary_provider = chain[0]` and calls `self.generate_json(..., provider_chain=[primary_provider])`. By passing a single-element list `['gemini']` instead of `chain`, it completely disables fallback to `groq` and `ollama` when `gemini` fails! The same bug exists in `adjudicate_aliases` (line 368).
2. In `backend/src/app/modules/ingestion/tasks.py` (line 213), `enrich_raw_product_task` enqueues `rate_ingredients` with `payload={"batch_size": 100}` (no `"ingredient_ids"` key).
   However, in `backend/src/app/modules/enrichment/tasks.py` (line 18), `rate_ingredients_task` checks `raw_ids = payload.get("ingredient_ids") or []` and immediately returns if `ingredient_ids` is empty!
3. In `backend/src/app/modules/ingredients/repository.py` (line 86), `find_unrated_ids` selects arbitrary unrated rows from the 23,197 CosIng rows without prioritizing ingredients that are actually attached to products in `product_ingredient`.

### Required Changes
1. **In `backend/src/app/modules/enrichment/service.py`:**
   - In `rate_ingredients`: change `provider_chain=[primary_provider]` to `provider_chain=chain`. For the second-opinion call (`if second_opinion and len(chain) > 1:`), select the first provider in `chain` that is different from `primary_res.provider` (`second_chain = [p for p in chain if p != primary_res.provider]`).
   - In `adjudicate_aliases`: change `provider_chain=[provider]` to `provider_chain=chain`.
2. **In `backend/src/app/modules/ingredients/repository.py`:**
   - Update `find_unrated_ids(self, limit: int = 100, only_product_linked: bool = False) -> list[uuid.UUID]` (using `sqlalchemy.text` so `ingredients` never imports `catalog.models`):
     ```python
     async def find_unrated_ids(
         self, limit: int = 100, only_product_linked: bool = False
     ) -> list[uuid.UUID]:
         linked_expr = text(
             "EXISTS (SELECT 1 FROM product_ingredient pi WHERE pi.ingredient_id = ingredient.id)"
         )
         stmt = select(Ingredient.id).where(
             Ingredient.rating.is_(None),
             Ingredient.rating_source != RatingSource.CURATED,
         )
         if only_product_linked:
             stmt = stmt.where(linked_expr)
         stmt = stmt.order_by(linked_expr.desc(), Ingredient.id.asc()).limit(limit)
         result = await self._session.execute(stmt)
         return list(result.scalars().all())
     ```
   - Expose `only_product_linked: bool = False` on `IngredientService.find_unrated_ingredient_ids(self, limit: int = 100, only_product_linked: bool = False) -> list[uuid.UUID]` in `backend/src/app/modules/ingredients/service.py`.
3. **In `backend/src/app/modules/enrichment/tasks.py` (`rate_ingredients_task`):**
   - If `payload.get("ingredient_ids")` is not provided, read `batch_size = int(payload.get("batch_size") or 50)` and fetch `ingredient_ids = await IngredientService(session).find_unrated_ingredient_ids(limit=batch_size, only_product_linked=True)`.
   - After `service.rate_ingredients(ingredient_ids)` finishes, enqueue `recompute_dirty_scores` via `enqueue_singleton_job(session, task_name="recompute_dirty_scores", payload={"batch_size": 500}, queue="default")`.
   - Check if more product-linked unrated ingredients remain (`remaining = await IngredientService(session).find_unrated_ingredient_ids(limit=1, only_product_linked=True)`); if non-empty, re-enqueue `enqueue_singleton_job(session, task_name="rate_ingredients", payload={"batch_size": batch_size}, queue="default")`.
4. **In `backend/src/app/modules/ingestion/tasks.py` (`enrich_raw_product_task`):**
   - When checking `matched_ids` for unrated ingredients (lines 207–216), collect `unrated_ids = [str(info.id) for info in infos.values() if info.rating is None]`.
   - If `unrated_ids` is non-empty, enqueue `await enqueue_job(session, queue="enrichment", task_name="rate_ingredients", payload={"ingredient_ids": unrated_ids})` in addition to the singleton fallback so newly scraped products get their ingredients rated immediately.

### Verification
```bash
uv run pytest tests/integration/test_enrichment_service.py -v
uv run mypy
uv run lint-imports
```

---

## Micro-Step 3: Unify Product & Ingredient Score Display + Seed `ratings_gold.csv`

### Root Cause
1. Product `6192440600200` (*Cica Silicone Gel*) returned `score: 70` and `score_coverage: 0.5`, while all 3 of its ingredients (`DIMETHICONE`, `CYCLOPENTASILOXANE`, `HUMULUS LUPULUS EXTRACT`) returned `rating: null, confidence: null, risk_level: "unknown"`.
2. This happened because `calculate_score` in `app/modules/scoring/engine.py` uses `resolve_effective_rating_and_confidence` (which derives `rating=8.0, confidence=0.5` from CosIng `functions` like `emollient`), whereas `_ingredient_out` in `app/modules/catalog/service.py` returned the raw `None` fields from the `ingredient` row!
3. Furthermore, `backend/tests/fixtures/ratings_gold.csv` has 156 curated skincare ingredients (including `DIMETHICONE` and `CYCLOPENTASILOXANE`), but `scripts/import_cosing.py` only loaded `seed_data.csv` (24 ingredients).

### Required Changes
1. **In `backend/src/app/modules/catalog/service.py` (`_ingredient_out`):**
   - Import `resolve_effective_rating_and_confidence` from `app.modules.scoring`.
   - In `_ingredient_out(position: int, raw_text: str, info: IngredientInfo | None) -> ProductIngredientOut`:
     When `info is not None`:
     ```python
     eff_rating = info.rating
     eff_conf = info.rating_confidence
     eff_risk = info.risk_level

     if eff_rating is None:
         derived_rating, derived_conf = resolve_effective_rating_and_confidence(
             IngredientScoreInput(
                 position=position,
                 rating=None,
                 confidence=0.0,
                 is_prohibited=info.is_prohibited,
                 is_restricted=info.is_restricted,
                 is_allergen=info.is_allergen,
                 functions=info.functions,
             )
         )
         if derived_rating is not None:
             eff_rating = derived_rating
             eff_conf = derived_conf
             if derived_rating >= 7.0:
                 eff_risk = RiskLevel.LOW
             elif derived_rating >= 4.0:
                 eff_risk = RiskLevel.MODERATE
             else:
                 eff_risk = RiskLevel.HIGH
     ```
     *Note:* When an ingredient has no `rating`, no `functions`, and no regulatory flags (such as in `test_a_known_but_unrated_ingredient_is_matched_yet_unknown`), `resolve_effective_rating_and_confidence` returns `(None, 0.0)`, so `eff_rating` stays `None` and `eff_risk` stays `RiskLevel.UNKNOWN`, preserving 100% compatibility with `tests/integration/test_products_api.py`!
2. **In `backend/scripts/import_cosing.py` (`load_seed_data`):**
   - Extend `load_seed_data(db: AsyncSession)` (or add `load_gold_seed_data(db: AsyncSession)` called by `load_seed_data`) to also read `BACKEND_DIR / "tests" / "fixtures" / "ratings_gold.csv"`.
   - For each row in `ratings_gold.csv` that is not already in `seed_data.csv`:
     - Compute `rating = Decimal(str(round((float(row["expected_rating_min"]) + float(row["expected_rating_max"])) / 2.0, 1)))` (or `Decimal("0.5")` if `is_prohibited == "true"`).
     - Set `risk_level = RiskLevel(row["expected_risk_level"].strip().lower())`, `rating_confidence = Decimal("1.0")`, `rating_source = RatingSource.CURATED`, `review_status = ReviewStatus.APPROVED`, `source_ref = row["source_ref"].strip()`.
     - Ensure primary normalized alias exists in `ingredient_alias` and baseline EN/FR translations exist in `ingredient_translation`.

### Verification
```bash
uv run pytest tests/integration/test_products_api.py tests/unit/test_scoring.py -v
```

---

## Micro-Step 4: Strict Ingredient Token Gatekeeper (Block `"1!!"`, `"1"`, `"N"`, `"(F01)"`, `"G2047548"`, `"0.1g"`)

### Root Cause
In `product_ingredient`, tokens like `"1!!"`, `"1"`, `"2"`, `"N"`, `"(F01)"`, `"G2047548"`, `"C142090"`, and `"0.1g"` were saved because `parse_ingredient_label` only checked `any(char.isalnum() for char in item)` and `normalize("1!!")` returned `"1"`.

### Required Changes
1. **In `backend/src/app/modules/ingredients/parser.py`:**
   - Define a pure validator function `is_valid_ingredient_token(text: str) -> bool`:
     ```python
     _ALPHA_CHARS_RE = re.compile(r"[a-zA-Z\u00C0-\u024F\u0400-\u04FF\u0600-\u06FF]")
     _FIL_OR_BATCH_CODE_RE = re.compile(
         r"^(?:\(?F\.?I\.?L\.?\b.*|\(?[A-Z]{1,2}\d{2,}[A-Z0-9/]*\)?)$",
         re.IGNORECASE,
     )
     _DOSAGE_ONLY_RE = re.compile(
         r"^\d+(?:[.,]\d+)?\s*(?:mg|g|gr|kg|ml|cl|l|oz|fl\.?\s*oz|%|iu|ui)$",
         re.IGNORECASE,
     )
     _HTML_ENTITY_JUNK_RE = re.compile(r"^(?:&?[lg]t;?|&?quot;?|&?amp;?)$", re.IGNORECASE)

     def is_valid_ingredient_token(text: str) -> bool:
         cleaned = text.strip()
         if len(cleaned) < 2 or len(cleaned) > 120:
             return False
         if len(_ALPHA_CHARS_RE.findall(cleaned)) < 2:
             return False
         if _FIL_OR_BATCH_CODE_RE.match(cleaned):
             return False
         if _DOSAGE_ONLY_RE.match(cleaned):
             return False
         if _HTML_ENTITY_JUNK_RE.match(cleaned):
             return False
         return True
     ```
   - Export `is_valid_ingredient_token` in `backend/src/app/modules/ingredients/__init__.py`.
   - Wait — check `tests/unit/test_parser.py` line 45:
     `("Aqua, 123, Glycerin", ["Aqua", "123", "Glycerin"]),  # digits are not junk (CI 77891)`
     **CRITICAL:** Because `tests/unit/test_parser.py` explicitly tests that `parse_ingredient_label("Aqua, 123, Glycerin")` returns `["Aqua", "123", "Glycerin"]`, do **not** drop `"123"` inside `parse_ingredient_label` itself!
     Instead:
     - In `looks_like_ingredient_list(parsed)` in `parser.py`, flag `invalid_tokens = [p.text for p in parsed if not is_valid_ingredient_token(p.text)]`; if `len(parsed) - len(invalid_tokens) < 2`, add `"fewer_than_2_valid_items"` to `reasons`.
     - In `IngredientService.ensure_ingredients_exist` (`app/modules/ingredients/service.py`), skip any item where `not is_valid_ingredient_token(clean_inci)`.
     - In `EnrichmentService.enrich_product` (`app/modules/enrichment/service.py`), filter `res.ingredients_inci` with `[item for item in res.ingredients_inci if is_valid_ingredient_token(item.inci or item.original) and is_valid_ingredient_token(item.original)]` BEFORE checking `if len(valid_ingredients) < 2: return EnrichmentOutcome(status=EnrichmentStatus.QUARANTINED, reason="insufficient_ingredients", result=res)`.
     - In `CatalogService.upsert_product` and `CatalogService.upsert_product_from_import` (`app/modules/catalog/service.py`), filter `data.ingredients` through `is_valid_ingredient_token(raw_text)` and re-index positions `1..N` contiguously!

### Verification
```bash
uv run pytest tests/unit/test_parser.py tests/integration/test_product_enrichment.py -v
```

---

## Micro-Step 5: Fix `"xx: "` Brand Prefixes & Translation Question-Mark Hygiene

### Root Cause
1. In `backend/src/app/modules/ingestion/mapper.py`:
   - Line 160 (`raw_brands = record.get("brands_tags") or record.get("brands")`) preferred OBF's slugified `brands_tags` (e.g., `xx:johnson-s-baby`) over the human-readable `brands` string (`Johnson's Baby`).
   - Line 155 (`if cleaned.lower().startswith(("en:", "fr:"))`) only stripped `en:` and `fr:`, leaving `xx:` and other 2-letter language prefixes intact.
   - Note from DB diagnostics: `BIO:VEGANE` is a legitimate brand with a 3-letter prefix before `:`, whereas OBF taxonomy prefixes are always **2 letters** (`^[a-zA-Z]{2}:`).
2. In `ingredient_translation`, any replacement characters (`\ufffd`) or mid-word `?` encoding artifacts from CSV imports or LLM outputs must be sanitized.

### Required Changes
1. **In `backend/src/app/modules/ingestion/mapper.py`:**
   - Update `_clean_brand_token(token: str) -> str`:
     ```python
     _OBF_LANG_PREFIX_RE = re.compile(r"^[a-zA-Z]{2}:\s*")

     def _clean_brand_token(token: str, from_tags: bool = False) -> str:
         cleaned = _OBF_LANG_PREFIX_RE.sub("", token.strip()).strip()
         if from_tags and cleaned and "-" in cleaned and " " not in cleaned and cleaned.islower():
             cleaned = cleaned.replace("-", " ").title()
         return cleaned
     ```
   - In `extract_brands(record: dict[str, Any])`:
     Prefer `record.get("brands")` first, falling back to `record.get("brands_tags")` only when `brands` is empty/missing. Pass `from_tags=bool(not record.get("brands") and record.get("brands_tags"))` to `_clean_brand_token`.
2. **In `backend/src/app/modules/catalog/repository.py` (`get_or_create_brand`):**
   - Strip `re.sub(r"^[a-zA-Z]{2}:\s*", "", brand_name.strip()).strip()` at the top of `get_or_create_brand` so no caller can ever persist a 2-letter `xx:` brand prefix.
3. **In `backend/src/app/modules/enrichment/validator.py` (`validate_and_clean_plain_text`):**
   - Strip `\ufffd` replacement characters (`cleaned = cleaned.replace("\ufffd", "")`).

### Verification
```bash
uv run pytest tests/unit/test_obf_mapper.py -v
```

---

## Micro-Step 6: Enforce Middleware Gate on OBF Import (`scripts/run_obf_import.py` & `app/modules/ingestion/importer.py`)

### Root Cause
In `some_errors2.txt`, 16,640 OBF products were written directly into `product` with `enrichment_status = 'pending'` and `image_status = 'none'` because `run_obf_import.py` called `import_product_record`, which bypassed validation/quarantine for invalid ingredient tokens and missing images.

### Required Changes
1. **In `backend/src/app/modules/ingestion/importer.py` (`import_product_record`):**
   - Filter `parsed_items` using `is_valid_ingredient_token(item.text)` and re-number positions `1..N`.
   - If fewer than 2 valid ingredients remain (`len(valid_items) < 2`), record skip `"fewer_than_2_valid_ingredients"`, route the record to `IngestionService(db).quarantine(raw_product_id=None, stage="obf_import", reason="insufficient_valid_ingredients", payload=row)`, and return `False` (never writing to `product`).
2. **In `backend/scripts/run_obf_import.py`:**
   - Ensure every imported record stores its `RawProduct` first so `raw_product_id` is available if `import_product_record` quarantines it, and enqueues `enrich_raw_product` for middleware enrichment.

### Verification
```bash
uv run pytest tests/integration/test_fallback_integration.py tests/unit/test_importer_name_normalized.py -v
```

---

## Micro-Step 7: Create & Execute `backend/scripts/sanitize_and_repipeline.py` (Way 2 In-Place Retro-Sanitizer)

### Purpose
Build an idempotent, transactional CLI script `backend/scripts/sanitize_and_repipeline.py` that scans the live PostgreSQL database, cleans all existing data in-place, routes broken/invalid records to `quarantine_item`, re-queues missing images to MinIO, rates unrated product-linked ingredients, and recomputes all dirty product scores.

### What `backend/scripts/sanitize_and_repipeline.py` MUST Do (In Exact Order)

1. **Step 1 — Seed Curated & Gold Set Ingredients (`seed_data.csv` + `ratings_gold.csv`):**
   - Call `await load_seed_data(session)` from `scripts.import_cosing` so all 24 `seed_data.csv` + 156 `ratings_gold.csv` ingredients have `rating_source = 'curated'`, `rating_confidence = 1.0`, and clean EN/FR translations.

2. **Step 2 — Purge Garbage `product_ingredient` & `ingredient` Rows (`"1!!"`, `"1"`, `"N"`, `"(F01)"`, `"G2047548"`, `"0.1g"`, etc.):**
   - Fetch all `ProductIngredient` rows where `not is_valid_ingredient_token(row.raw_text)`.
   - Delete those invalid `product_ingredient` rows, and re-number the remaining `product_ingredient.position` values (`1..N`) contiguously per affected `product_id` (using a two-pass offset `+1000` then `1..N` to respect the primary key `(product_id, position)`).
   - Mark all affected products `score_dirty = True`.
   - Scan `Ingredient` rows where `not is_valid_ingredient_token(ing.inci_name)`: delete any remaining `product_ingredient` references to them, and delete those garbage `Ingredient` rows from `ingredient`.

3. **Step 3 — Quarantine & Remove Products With `< 2` Valid Ingredients:**
   - Find all `Product` rows that now have `< 2` `product_ingredient` rows.
   - For each such product, create a `quarantine_item` via `IngestionService(session).quarantine(raw_product_id=None, stage="post_audit", reason="insufficient_valid_ingredients", payload={"barcode": p.barcode, "name": p.name, "raw_ingredients_text": p.raw_ingredients_text, "source": p.source.value})` and delete the product from `product`.

4. **Step 4 — Clean & Merge `"xx: "` Prefixed Brands (`^[a-zA-Z]{2}:\s*`):**
   - Find all `Brand` rows matching `^[a-zA-Z]{2}:\s*` (preserving 3-letter `BIO:VEGANE`).
   - For each prefixed brand, compute the clean name via `_clean_brand_token(b.name, from_tags=True)`.
   - If a `Brand` with `lower(name) == lower(clean_name)` already exists, update `product.brand_id` to point to the existing clean `Brand` and delete the prefixed `Brand`.
   - Otherwise, update `b.name = clean_name` in-place.

5. **Step 5 — Repair Corrupted (`?` / `chr(65533)`) Ingredient Translations:**
   - Query `IngredientTranslation` joined with `Ingredient` where `strpos(rationale, chr(65533)) > 0 OR rationale ~ '[a-zA-ZÀ-ÿ]\?[a-zA-ZÀ-ÿ]' OR strpos(coalesce(summary, ''), chr(65533)) > 0`.
   - Regenerate clean UTF-8 `summary`, `concern_note`, and `rationale` for those rows using the ingredient's `functions` and regulatory flags.

6. **Step 6 — Re-Treat Products With Missing or Unprocessed Images (`image_url IS NULL` or Non-CDN URLs):**
   - For products where `image_source_url IS NOT NULL` (or `image_url IS NOT NULL` and not starting with `settings.image_cdn_base_url`) and `image_status != 'processed'`:
     - Ensure `image_source_url = COALESCE(image_source_url, image_url)` and `image_status = 'candidate'`.
     - Enqueue `process_product_image` jobs (up to `--image-batch-limit`, default `200`) into the `enrichment` queue.
   - For products where `image_url IS NULL AND image_source_url IS NULL` and `source == 'scrape'`:
     - Enqueue `enrich_raw_product` (if a matching `raw_product` exists) or record in `quarantine_item` (`stage="image_pipeline"`, `reason="missing_image"`).

7. **Step 7 — Reset Failed Jobs, Rate Product-Linked Unrated Ingredients, & Recompute Dirty Scores:**
   - Delete or reset `Job` rows where `status = 'failed' AND task_name = 'rate_ingredients'`.
   - Run `CatalogService(session).rematch_unmatched(batch_size=1000)` in a loop until `0` newly matched rows remain.
   - Enqueue `rate_ingredients` (or if `--rate-now` flag is passed, call `EnrichmentService(session).rate_ingredients(...)` directly on up to `--rate-limit` product-linked unrated ingredients).
   - Run `CatalogService(session).recompute_dirty_scores(batch_size=500)` in a loop until all dirty/stale products are rescored!
   - If `--drain-worker` is passed, run `run_pending_jobs` on queues `["enrichment", "default"]` (up to `--max-jobs`, default `200`).

### Run the Script Against the Live Database
```bash
uv run python scripts/sanitize_and_repipeline.py --rate-now --rate-limit 100 --drain-worker --max-jobs 100
```

---

## Micro-Step 8: Add Regression Tests & Run the Full Quality Gate

1. **Add Unit/Integration Tests in `backend/tests/unit/test_overhaul_sanitizers.py`:**
   - Test `is_valid_ingredient_token`:
     - Asserts `False` for `"1!!"`, `"1"`, `"20"`, `"N"`, `"a"`, `"(F01)"`, `"G2047548"`, `"C142090"`, `"0.1g"`, `"&lt"`, `""`.
     - Asserts `True` for `"AQUA"`, `"GLYCERIN"`, `"1,2-HEXANEDIOL"`, `"CI 77891"`, `"TOCOPHEROL"`, `"PEG-40 HYDROGENATED CASTOR OIL"`.
   - Test `_clean_brand_token`:
     - Asserts `_clean_brand_token("xx:unil", from_tags=True) == "Unil"`.
     - Asserts `_clean_brand_token("xx:johnson-s-baby", from_tags=True) == "Johnson S Baby"`.
     - Asserts `_clean_brand_token("BIO:VEGANE", from_tags=False) == "BIO:VEGANE"`.
   - Test `_ingredient_out` heuristic consistency:
     - When `IngredientInfo` has `rating=None`, `functions=("emollient", "skin conditioning")`, `_ingredient_out` returns `rating=8.0`, `confidence=0.5`, `risk_level=RiskLevel.LOW`.
     - When `IngredientInfo` has `rating=None`, `functions=()`, `is_prohibited=False`, `_ingredient_out` returns `rating=None`, `confidence=None`, `risk_level=RiskLevel.UNKNOWN`.

2. **Run All Backend Quality Gates:**
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run pytest
```

3. **Run Post-Execution Database Verification:**
```bash
docker exec -i skincare-db-1 psql -U skincare -d skincare -c "
SELECT name FROM brand WHERE name ~ '^[a-zA-Z]{2}:' LIMIT 10;
SELECT raw_text, count(*) FROM product_ingredient WHERE raw_text !~ '[a-zA-Z]{2}' GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
SELECT rating_source, risk_level, count(*) FROM ingredient GROUP BY 1, 2 ORDER BY 3 DESC;
SELECT id, task_name, status, attempts, left(error, 80) FROM job ORDER BY created_at DESC LIMIT 10;
"
uv run python scripts/quality_report.py
```
