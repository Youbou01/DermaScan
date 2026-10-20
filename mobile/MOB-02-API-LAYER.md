# MOB-02 API Layer: Implementation and Test Guide

This document records the API layer delivered for MOB-02, its contract boundaries, and the checks
to run before opening or updating a pull request.

## What was added

- **Generated API contract:** `openapi.json` and `src/api/generated/schema.d.ts` are generated from
  the FastAPI app. `src/api/types.ts` exports the mobile-facing types from the generated schema;
  API response shapes should not be hand-written or guessed.
- **Environment and client:** `src/config/env.ts` validates `EXPO_PUBLIC_API_URL` and
  `EXPO_PUBLIC_USE_MOCKS`. The URL must be the server origin (no path); the client uses the
  `/api/v1/...` paths and normalizes away a trailing slash. Mock mode can use a reserved
  `https://mock.invalid` base URL when no API URL is provided.
- **Typed HTTP client:** `src/api/client.ts` builds an `openapi-fetch` client from the generated
  `paths` type. An outgoing request middleware sets `Accept-Language` from the active API locale.
- **Problem details:** `src/api/errors.ts` defines `ApiError`. RFC problem responses preserve
  `type`, `title`, HTTP `status`, `detail`, `instance`, `request_id`, and validation `errors`.
  Non-problem HTML or JSON responses become a safe `about:blank` / `Request failed` error, while
  retaining the HTTP status and request ID header when available.
- **Query hooks:** `src/api/hooks.ts` provides home, categories, product-by-ID,
  product-by-barcode, search, and product ingredient-breakdown queries. Their keys include the
  request parameters. `src/api/query-client.ts` sets a 30-second stale time and one retry; the
  root Expo layout provides the QueryClient.
- **Mock fixtures:** `src/api/fixtures.ts` contains typed English and French home/category data,
  product detail, and ingredient breakdown data. `src/api/client.ts` routes supported API paths to
  these fixtures when mocks are enabled. `src/api/search-fixture.ts` provides filtered mock search
  results.
- **Generated schema workflow:** `npm run api:generate` exports backend OpenAPI and regenerates
  `openapi.json` and `src/api/generated/schema.d.ts`.
- **Demo-seed idempotency:** `backend/scripts/seed_demo.py` now reuses curated ingredients by
  case-insensitive INCI name or normalized aliases, adds only missing aliases, and reports
  conflicting alias ownership clearly. An integration test verifies reuse and repeatability.

## Contract boundaries and follow-up

- The generated backend schema currently documents home, categories, and product endpoints.
- The backend OpenAPI schema does **not** yet define a search endpoint. Real-network search
  therefore returns `ApiContractUnavailableError`; search is implemented in mock mode only, using
  the proposed contract fixture in `../docs/search-api-contract.md`.
- There is no standalone ingredient-detail endpoint in the generated schema. The ingredient
  breakdown hook reads `ingredients` from the typed product-detail endpoint. The fixture uses that
  same product schema.
- `setApiLocale()` and `getActiveApiLocale()` are the locale bridge in `src/api/locale.ts`. Wire
  `setApiLocale()` to the real i18n language-change event when the app i18n provider is integrated;
  API requests currently derive the initial locale from the device and default to English.
- The demo products are not scored by `seed_demo.py`. Run the backend score recomputation job if
  you need scores for eligible demo products. Records with insufficient ingredient coverage can
  correctly remain unscored.

## Tests added and what they cover

| Test file                                     | Coverage                                                                                                                                                                                                           |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/api/api.test.ts`                         | Active `Accept-Language`; RFC problem parsing including validation errors and request ID; HTML/unformatted JSON fallback; localized mock home/categories/product/ingredients; complete search fixture shape.       |
| `src/api/hooks.test.tsx`                      | Hook success and data; query-key structure; caching, stale time and retry defaults; product, barcode and ingredient queries; normalized search query key; typed `ApiError` failure; no network fetch in mock mode. |
| `src/config/env.test.ts`                      | Environment parsing, URL validation, mock-mode fallback, and boolean validation.                                                                                                                                   |
| `src/__tests__/app/home-route.test.tsx`       | Home route renders through its route contract.                                                                                                                                                                     |
| `src/__tests__/app/not-found-route.test.tsx`  | Not-found route behavior.                                                                                                                                                                                          |
| `backend/tests/integration/test_seed_demo.py` | Existing curated Aqua is reused and running the demo seeder twice does not duplicate it or the demo products. Uses the rollback-isolated PostgreSQL integration fixture.                                           |

The last verified mobile run reported **5 suites and 24 tests passing**. The last verified backend
run reported **365 tests passing**.

## Run mobile checks

Use Node.js 22.13 or newer and run from `mobile/`:

```bash
cd mobile
npm ci
npx expo install --check
npx expo-doctor
npm run check
```

`npm run check` runs TypeScript (`tsc --noEmit`), ESLint, Prettier check, and Jest. Run a single
test file with:

```bash
npm test -- --runInBand src/api/api.test.ts
npm test -- --runInBand src/api/hooks.test.tsx
```

When backend API contracts change, regenerate the mobile types from `mobile/`:

```bash
npm run api:generate
npm run check
```

Commit `package-lock.json` with dependency changes. Do not use `npm audit fix --force` as a generic
fix: the audit output for this dependency tree proposed breaking SDK downgrades. Review findings
and update the Expo-compatible dependency set only when a compatible remediation is available.

## Configure and run the app

Copy `mobile/.env.example` to `mobile/.env`. Set the backend **root URL**, without `/api/v1`:

| Runtime                          | `EXPO_PUBLIC_API_URL`           |
| -------------------------------- | ------------------------------- |
| Android emulator                 | `http://10.0.2.2:8000`          |
| iOS simulator                    | `http://localhost:8000`         |
| Physical phone on the same Wi-Fi | `http://<computer-LAN-IP>:8000` |

Set `EXPO_PUBLIC_USE_MOCKS=false` for backend requests or `true` to use fixtures without a running
backend. `EXPO_PUBLIC_*` values are bundled into the app and must not contain secrets. Restart
Expo after changing `.env`:

```bash
npx expo start --clear
```

For a real phone, run the API bound to all interfaces (`--host 0.0.0.0`) and use the computer's
LAN IP. A phone's `localhost` points to the phone itself.

## Run backend checks

Run from `backend/`; Docker must be available for the PostgreSQL integration tests unless
`TEST_DATABASE_URL` points to a disposable database whose name contains `test`:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run alembic upgrade head
uv run alembic check
uv run pytest
```

`alembic upgrade head` applies migrations to the configured database; use the intended local or
test database. The integration-test fixture runs each test in a rolled-back transaction.

## Manual API smoke test

With the local backend migrated and running, seed the demo data once (the seeder is safe to rerun),
then check category localization and the known demo barcode:

```bash
cd backend
uv run python scripts/seed_demo.py
curl -i http://localhost:8000/api/v1/categories
curl -i -H 'Accept-Language: fr' http://localhost:8000/api/v1/home
curl -i http://localhost:8000/api/v1/products/by-barcode/6190000000019
```

To recompute scores for stale products, run `uv run python scripts/recompute_scores.py`. A 404 for
the demo barcode means the seeder has not populated the database used by the running API. A null
score on a recently added card can be expected when the product has not been scored or has
insufficient recognized ingredient coverage.

## Pre-push checklist

- [ ] `mobile/npm run check` passes.
- [ ] Backend Ruff, formatting, mypy, import contracts, Alembic check, and pytest pass.
- [ ] Generated schema is current if backend OpenAPI changed.
- [ ] `.env` files remain local and are not staged; no public environment variable contains a
      secret.
- [ ] Search and ingredient limitations above are understood; do not treat mock search as a live
      backend endpoint.
- [ ] Review npm audit findings separately; never apply the suggested breaking SDK downgrade
      automatically.
