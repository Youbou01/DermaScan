# MOB-09 Filters: Implementation and Test Guide

This document records the filter sheet delivered for MOB-09, its contract boundaries, and the
checks to run before opening or updating a pull request.

## What was added

- **Filter state:** `src/features/filters/filter-state.ts` exports the `FilterState` type
  (`category`, `bands`, `minScore`, `maxScore`, `include`, `exclude`) and the helpers `clearAll`,
  `toggleBand`, `isScoreRangeValid`, `addIngredient`, `removeIngredient` and
  `countActiveFilters`. Bands use the generated `RiskLevel` type. An ingredient name is trimmed and
  compared without case. Adding it to one list removes it from the other. Each list holds 10 names
  at most, like the backend.
- **Route params:** `src/features/filters/filter-params.ts` exports `encodeFilters` and
  `decodeFilters`. Empty filters give no params. `band` is one comma-separated text. `include` and
  `exclude` are JSON text, so names with a comma survive. An array param keeps its first value. An
  unknown band, a score outside 0-100 or a broken JSON is ignored and never throws.
- **Filter sheet:** `src/features/filters/FilterSheet.tsx` is a bottom sheet with category, risk
  band (low, moderate, high, insufficient data), score range and two ingredient lists. It works on
  a draft copy: the real filters change only when the user presses "Show results". "Clear all"
  applies empty filters at once. A minimum score above the maximum shows a message and disables
  "Show results". Selected options show a check mark, not only a color. Every control is 44pt high.
  The two footer buttons have horizontal and vertical padding and centered text, so the long
  "Show results" label does not touch the button edges.
- **Ingredient chips:** `src/features/filters/IngredientChips.tsx` has a text field, suggestions and
  removable chips. Only suggested names can be added, because the backend returns an empty page
  when an `include` name is unknown.
- **Mock suggestions:** `src/features/filters/ingredient-suggestions.ts` holds a local list of
  ingredient names. It is a mock: no backend endpoint suggests ingredient names yet.
- **Translations:** 9 new `filters.*` keys were added to both `src/i18n/en.json` and
  `src/i18n/fr.json` (a test checks that both files have identical keys). `common.clear_all` and
  `common.close` are reused.

## Contract boundaries and follow-up

- **Backend filters (D9)** are used as specified: `category` (children included), `band` (array of
  `RiskLevel`), `min_score`, `max_score`, `include` and `exclude` (arrays, 10 names at most).
  Arrays are sent by repeating the name (`band=low&band=high`). A comma returns 422. This was
  checked with curl. On a phone, selecting two risk bands returned a normal page (HTTP 200), which
  would not happen with a comma, so the app sends repeated names. The exact query string is not in
  the API access log (it logs the path only).
- **Naming difference to handle when wiring.** `FilterState` names the list `bands` (plural), but
  the list query `ProductListFilters` (PR #36) reads `band` (singular). Passing the state as it is
  silently drops the risk filter, and TypeScript does not report it. Pass
  `{ ...filters, band: filters.bands }`. The other fields (`minScore`, `maxScore`, `include`,
  `exclude`, `category`) have the same names on both sides.
- **Insufficient data band.** `/products/filter` returns scored products only. Imported products
  without a score cannot appear, so this option returns only part of the products with
  insufficient data (2 sample products on the local database). The sheet still shows it because
  MOB-09 asks for the risk band. This is how D9 is specified, not a mobile bug. The team can decide
  whether the backend should change.
- **High band on local data.** The local database has no product in the high band, so selecting it
  alone shows the empty state. This is the data, not a bug. Counts per band on the local database:
  low 7 (scores 75-84), moderate 16 (56-74), high 0, unknown 2 (40).
- **Ingredient names.** `include` and `exclude` take names, not ids. They go through the alias
  pipeline, and matching ignores case and accents. If one `include` name is unknown, the whole page
  is empty. An unknown `exclude` name is ignored.
- **Autocomplete.** No endpoint suggests ingredient names (it is not in D9, US-06 or the backlog).
  The chips use the local mock list until the team adds one.
- **Text and filters.** `/products/filter` has no `q` and `/products/search` takes no filters, so
  they cannot be combined on the real backend yet. With a text query the list calls `/search` and
  the filters have no effect. Asking the backend team to add `q` to `/products/filter` (or the
  filters to `/products/search`) is the open decision.
- **Score range.** `min_score` greater than `max_score` returns 422, so the sheet does not allow it.
- **Local data.** No product has both a score and ingredients, so include and exclude cannot be
  seen with real results on the local database. They are checked in Jest.
- **Not wired yet.** `ProductList`, `ProductListFilters` and `/products` exist only in PR #36
  (MOB-07, frozen). This branch does not touch them, and the sheet is not opened from any screen.
  After PR #36 is merged, wire it in `/products`: read the params with `decodeFilters`, pass them
  to the list query (with `band: filters.bands`), and keep `q` in the route when applying.
- **Ordering** is decided by the backend. The UI never re-sorts or computes a score.

## Tests added and what they cover

| Test file                                              | Coverage                                                                                                                            |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `src/features/filters/filter-state.test.ts`            | Empty start, band toggle, score range check, trimmed and repeated names, move between lists, limit of 10, remove, count, clear all. |
| `src/features/filters/filter-params.test.ts`           | Empty filters, round trip, names with a comma, array params, invalid values ignored, limit of 10.                                   |
| `src/features/filters/FilterSheet.test.tsx`            | Apply band and category, insufficient data option shown, clear all, minimum above maximum blocked.                                  |
| `src/features/filters/IngredientChips.test.tsx`        | Add a suggestion, no suggestion for an unknown name, case ignored, remove a chip.                                                   |
| `src/features/filters/FilterSheetIngredients.test.tsx` | An included ingredient is applied from the sheet.                                                                                   |

On a local test branch with `mobile/mob-07` merged, `npm run check` reported **19 suites and 89
tests passing**. On `mobile/mob-09` alone the full check passed in the pre-commit hook. Jest prints
a "worker process failed to exit gracefully" warning (a leaked timer); it is not a failure.

## Run mobile checks

Use Node.js 22.13 or newer and run from `mobile/`:

```bash
cd mobile
npm ci
npm run check
```

Run the MOB-09 tests individually with:

```bash
npm test -- --runInBand src/features/filters/filter-state.test.ts
npm test -- --runInBand src/features/filters/filter-params.test.ts
npm test -- --runInBand src/features/filters/FilterSheet.test.tsx
npm test -- --runInBand src/features/filters/IngredientChips.test.tsx
npm test -- --runInBand src/features/filters/FilterSheetIngredients.test.tsx
```

## Run and inspect the UI

The sheet is not reachable from a screen on this branch. After PR #36 is merged, or on a
throw-away local branch with `mobile/mob-07` merged (never pushed):

```bash
git checkout -b test/mob-09-with-mob-07 mobile/mob-09
git merge mobile/mob-07
```

On that test branch only, wire the sheet in `src/app/products.tsx` (a "Filters (n)" button that
opens `FilterSheet`, reads the params with `decodeFilters`, and passes
`{ ...filters, band: filters.bands }` to `ProductList`). Do not commit this wiring to
`mobile/mob-09`. Then run the real backend as described in `MOB-07-PRODUCT-LIST.md` and start
Expo with `npx expo start --lan --clear`. What to check on the phone:

1. Open the sheet. Pick a category, a band and a score range. The list shows only matching products.
2. Select two risk bands. The list shows products of both bands (for example low + moderate gives
   scores 56-84 on the local data).
3. Select only the high band. The empty state appears (no such product locally).
4. Enter a minimum score above the maximum. A message appears and "Show results" is disabled.
5. Press "Clear all". Every filter is cleared and the counter returns to 0.
6. Type `aq` in "Must contain". `Aqua` is suggested. Add it, it becomes a chip `Aqua ×`, then remove
   it by pressing the chip.
7. Select "Insufficient data". Only 2 products appear (known backend limit).

The contract was checked with curl against the local API (`limit` must stay at 50 or less):

```bash
curl -s 'http://localhost:8000/api/v1/products/filter?band=unknown&band=low&limit=3'
curl -s -o /dev/null -w '%{http_code}\n' 'http://localhost:8000/api/v1/products/filter?band=low,high&limit=3'
```

The first returns a page. The second returns 422.

## Main files

| File                                             | Purpose                          |
| ------------------------------------------------ | -------------------------------- |
| `src/features/filters/filter-state.ts`           | Filter state type and helpers    |
| `src/features/filters/filter-params.ts`          | Route params encode and decode   |
| `src/features/filters/FilterSheet.tsx`           | Filter sheet                     |
| `src/features/filters/IngredientChips.tsx`       | Ingredient chips and suggestions |
| `src/features/filters/ingredient-suggestions.ts` | Mock ingredient names            |
| `src/i18n/en.json`, `src/i18n/fr.json`           | `filters.*` strings              |

## Pre-push checklist

- [ ] `mobile/npm run check` passes.
- [ ] `en.json` and `fr.json` have identical keys.
- [ ] `.env` files remain local and are not staged; no public environment variable contains a
      secret.
- [ ] No file of PR #36 was changed: `git diff --stat origin/main` shows only
      `src/features/filters`, the two dictionaries and this guide.
- [ ] The sheet was checked on a phone on a local test branch with `mobile/mob-07` merged, or the PR
      says that it was not.
- [ ] The test branch is never pushed. Push only `git push -u origin mobile/mob-09`.
- [ ] The PR is opened against `main`, and its description says that the wiring into `/products`
      waits for PR #36, and mentions the `bands` / `band` naming.
- [ ] Known limits understood: insufficient data band, mock suggestions, text and filters cannot be
      combined.
