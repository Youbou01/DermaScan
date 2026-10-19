# Manual test guide — D1, D2, D6, D10

For teammates on **Windows (PowerShell)**. Each section is copy/pasteable. You can also use Swagger at http://localhost:8000/docs.

---

## Section 0 — Setup (once)

```powershell
cd C:\Users\dunno\Desktop\fs\dermaScan\DermaScan
git checkout translations-homepageEP
git pull

cd backend
uv sync
copy .env.example .env
# Edit .env: replace both CHANGE_ME with the same password (POSTGRES_PASSWORD and DATABASE_URL).

docker compose up -d db
uv run alembic upgrade head
uv run python scripts/seed_categories.py
uv run uvicorn app.main:create_app --factory --reload
```

| What | URL / command |
|---|---|
| API | http://localhost:8000 |
| Swagger / OpenAPI | http://localhost:8000/docs |
| Ready probe | `Invoke-RestMethod http://localhost:8000/health/ready` |

**Compose service name:** `db` (project name `skincare`). Credentials come from `.env` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).

### Sample products (~30) for home-feed browsing

```powershell
# Requires categories already seeded.
uv run python scripts/seed_home_sample.py

# Remove them later:
uv run python scripts/seed_home_sample.py --purge
```

Barcodes look like `619000100000` + check digit (printed by the script). Demo barcodes from `seed_demo.py` (optional): `6190000000019`, `6190000000026`, `6190000000033`.

### Freeze the Top-rated rotation day

In `.env` (or the process environment):

```text
HOME_FEED_DATE=2026-10-19
```

Restart uvicorn after changing it. Leave unset for real UTC today.

### Inspect the database

```powershell
docker compose exec db psql -U skincare -d skincare
```

---

## D1 — Category seed + tree endpoint

**Goal:** Idempotent en/fr category tree with stable slugs; `GET /api/v1/categories` returns parents with children.

**Done when:** Seed twice → same row counts; API tree matches `docs/categories-slugs.md`.

### Steps

1. Seed (twice):

```powershell
uv run python scripts/seed_categories.py
uv run python scripts/seed_categories.py
```

Expected: second run prints `touched=0` (or a low number if you edited names).

2. English tree:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/categories | ConvertTo-Json -Depth 5
```

Expected: status 200; top-level slugs `body-care`, `face-care`, `lip-care`, `sun-care`; `face-care.children` includes `cleanser`, `moisturizer`, …

3. French tree:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/categories -Headers @{ "Accept-Language" = "fr" }
```

Expected: `face-care` name = `Soin du visage`; child `cleanser` = `Nettoyant`.

4. Database check (inside `psql`):

```sql
SELECT COUNT(*) FROM category;                 -- 15
SELECT COUNT(*) FROM category_translation;    -- 30
SELECT c.slug, p.slug AS parent
FROM category c
LEFT JOIN category p ON p.id = c.parent_id
ORDER BY c.slug;
```

### Edge cases

- Run seed twice → no duplicate slugs (`SELECT slug, COUNT(*) FROM category GROUP BY slug HAVING COUNT(*) > 1` → 0 rows).
- Empty DB before seed → API returns `[]` until you seed.

### Common problems

| Problem | Fix |
|---|---|
| `Categories missing` later in sample seed | Run `seed_categories.py` first |
| Connection refused | `docker compose up -d db` and check `.env` passwords match |
| Slug docs | See repo root `docs/categories-slugs.md` |

---

## D2 — Locale resolution + translation fallback

**Goal:** `Accept-Language` → `en`/`fr` with English fallback; responses set `Content-Language` and `Vary`.

**Done when:** Header cases below match; category missing French falls back to English.

### Steps

```powershell
# Missing header → English
(Invoke-WebRequest http://localhost:8000/api/v1/categories).Headers["Content-Language"]
# expect: en

# fr-TN → French
$r = Invoke-WebRequest http://localhost:8000/api/v1/categories -Headers @{ "Accept-Language" = "fr-TN" }
$r.Headers["Content-Language"]   # fr
$r.Headers["Vary"]               # includes Accept-Language

# de → English fallback
(Invoke-WebRequest http://localhost:8000/api/v1/categories -Headers @{ "Accept-Language" = "de" }).Headers["Content-Language"]
# expect: en
```

Unit tests (no Docker):

```powershell
uv run pytest tests/unit/test_i18n.py -v
```

### Edge cases

- Malformed header (`!!!;;;,,`) → `en`, never 500.
- Quality values: `en;q=0.5,fr;q=0.9` → `fr`.

### Common problems

| Problem | Fix |
|---|---|
| Always English | Confirm you send `Accept-Language` (Swagger “Authorize” does not set this; use “Try it out” headers or PowerShell) |

---

## D6 — Home feed + section load-more

**Goal:** `GET /api/v1/home` returns three sections; product shelves paginate with opaque cursors; Top-rated rotates by UTC date.

**Done when:** Empty DB → 200 with empty lists; invalid cursor → 400 problem+json; infinite scroll has no duplicates.

### Steps

1. Empty / seeded feed:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/home?limit=5" | ConvertTo-Json -Depth 6
```

Expected sections in order: `categories`, `top_rated`, `recently_added`. Each has `id`, `type`, `title`, `items`, `next_cursor`.

2. French titles:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/home" -Headers @{ "Accept-Language" = "fr" }
```

Expected titles: `Catégories`, `Mieux notés`, `Ajoutés récemment`.

3. Infinite scroll (Top rated):

```powershell
$feed = Invoke-RestMethod "http://localhost:8000/api/v1/home?limit=5"
$cursor = ($feed.sections | Where-Object id -eq "top_rated").next_cursor
$page2 = Invoke-RestMethod "http://localhost:8000/api/v1/home/sections/top_rated?limit=5&cursor=$cursor"
# Confirm IDs in page2 do not overlap the first page.
```

4. Daily rotation (no code edit):

```powershell
$env:HOME_FEED_DATE = "2026-10-19"
# restart uvicorn in that shell, call /home, note top_rated order
$env:HOME_FEED_DATE = "2026-10-20"
# restart again — same products, different order when scores tie
```

5. Bad cursor / bad limit:

```powershell
try {
  Invoke-WebRequest "http://localhost:8000/api/v1/home/sections/top_rated?cursor=not-a-cursor"
} catch {
  $_.Exception.Response.StatusCode.value__   # 400
  $_.ErrorDetails.Message                    # type urn:skincare:problem:invalid-cursor
}

try {
  Invoke-WebRequest "http://localhost:8000/api/v1/home?limit=0"
} catch {
  $_.Exception.Response.StatusCode.value__   # 400 invalid-limit
}
```

### Database checks

```sql
SELECT name, score, score_band, created_at FROM product ORDER BY score DESC NULLS LAST LIMIT 20;
-- Null score / score_band = 'unknown' must NOT appear in Top rated, but may appear in Recently added.
```

### Common problems

| Problem | Fix |
|---|---|
| Top rated empty | Insert scored products (`seed_home_sample.py`) with `score IS NOT NULL` and `score_band <> 'unknown'` |
| Cursor 400 after midnight | Expected if you mix days without embedding — our cursors embed the seed date; keep using the cursor from the first page |
| `HOME_FEED_DATE` ignored | Restart uvicorn; variable must be set in the same environment as the process |

---

## D10 — Automated integration tests

**Goal:** Real-Postgres coverage for categories, home feed, and (via existing file) product/barcode endpoints.

### Run

```powershell
cd backend
docker compose up -d db   # Docker must be running (testcontainers or TEST_DATABASE_URL)

uv run pytest                                      # full suite
uv run pytest tests/integration/test_categories_api.py -v
uv run pytest tests/integration/test_home_api.py -v
uv run pytest tests/integration/test_products_api.py -v
uv run pytest tests/integration/test_home_api.py::test_home_feed_empty_database -v
```

Quality gates (same as CI / CONTRIBUTING):

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
```

### Reading a failure

- Assertion error → expected vs actual in the traceback.
- `application/problem+json` mismatch → check `type` URN, not only status code.
- Docker errors → start Docker Desktop; or set `TEST_DATABASE_URL` to a DB whose name contains `test`.

### Coverage table

| Test | Proves |
|---|---|
| `test_category_tree_english_and_french` | en/fr/`fr-TN`/`de` + Content-Language/Vary |
| `test_category_missing_french_falls_back_to_english` | Translation fallback |
| `test_empty_categories_returns_empty_list` | Empty DB → 200 `[]` |
| `test_seed_categories_is_idempotent` | Seed twice → 15 cats / 30 translations |
| `test_seeded_tree_structure_via_api` | Parent/child slugs stable |
| `test_home_feed_empty_database` | Three empty sections, 200 |
| `test_home_feed_french_titles_and_categories` | Localized section titles |
| `test_home_feed_single_product_and_null_score_excluded_from_top_rated` | Null/unknown excluded from Top rated; present in Recent |
| `test_home_feed_pagination_walk_collects_each_product_once` | Keyset walk, no dupes/gaps |
| `test_home_feed_exact_page_size_has_no_next_cursor` | Exactly page size → `next_cursor` null |
| `test_home_feed_page_size_plus_one_has_next_cursor` | Page size + 1 → cursor |
| `test_home_feed_last_page_has_null_cursor` | Last page |
| `test_recently_added_pagination_walk_no_duplicates` | Recent shelf pagination |
| `test_top_rated_order_stable_same_day_changes_next_day` | Daily rotation |
| `test_cursor_from_day_n_still_paginates_on_day_n_plus_1` | Seed date embedded in cursor |
| `test_invalid_cursor_and_wrong_section_return_400_problem` | Garbage / wrong-section → 400 |
| `test_limit_out_of_range_is_400` | limit 0/51/-1 |
| `test_unknown_section_is_404` | Unknown section id |
| `test_product_card_shape` | Light card fields |
| **D4/D5 (existing `test_products_api.py`, not modified)** | Detail contract, label order, unmatched→unknown, UPC-A/EAN-8, 404/422 problem+json, Accept-Language, OpenAPI |
| **Expected failures** | None found; no `xfail` markers added |

---

## Quick SQL cleanup (optional)

```sql
DELETE FROM product WHERE source_id LIKE 'home-sample-%';
-- Or: uv run python scripts/seed_home_sample.py --purge
```
