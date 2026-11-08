# MOB-08 Search: Implementation and Test Guide

This document records the search screen delivered for MOB-08, its contract boundaries, and the
checks to run before opening or updating a pull request.

## What was added

- **Recent searches storage:** `src/features/search/recent-searches.ts` exports
  `loadRecentSearches`, `addRecentSearch` and `MAX_RECENT_SEARCHES` (5). Terms are saved in
  AsyncStorage, newest first. Terms shorter than 2 characters are ignored, and a repeated term
  (compared case-insensitively) moves to the top instead of being duplicated. A storage failure
  leaves the list empty or unsaved, and search still works.
- **Debounce hook:** `src/features/search/useDebouncedValue.ts` exports `useDebouncedValue` and
  `SEARCH_DEBOUNCE_MS` (300).
- **Search screen:** `src/features/search/SearchScreen.tsx` has a text input, a Search button and
  the list of recent searches. Submitting (button or keyboard search key) trims the text. A text
  shorter than 2 characters shows a hint and does nothing else. Otherwise the term is saved and
  the app opens `/products?q=<text>`. Pressing a recent search does the same.
- **Route:** `src/app/search.tsx` renders the screen at `/search`.
- **Home entry point:** `HomeHero` in `src/features/home/HomeScreen.tsx` has a "Search products"
  button under the scan button. It reuses the scan button styles (44pt minimum height).
- **Translations:** 7 `search.*` keys were added to both `src/i18n/en.json` and
  `src/i18n/fr.json` (a test checks that both files have identical keys).

## Contract boundaries and follow-up

- **MOB-08 does not render results.** Results are shown by `ProductList` and the
  `/products?q=<text>` route, which exist only in PR #36 (MOB-07). Until PR #36 is merged,
  `/search` on this branch opens a route that does not exist. Merge PR #36 first.
- **Text query** (2 or more characters) calls `GET /api/v1/products/search` (`q`, `limit`,
  `cursor`) through the MOB-07 query. In real mode the category is ignored when a text query is
  present. Combining text and filters is a MOB-09 concern and depends on the backend.
- **Search runs on submit only.** The debounce is used for the "type at least 2 characters"
  hint, so it does not flash on every key press. Search-as-you-type is not implemented.
- **Ordering** is decided by the backend. The UI never re-sorts.
- Not part of MOB-08: filters (MOB-09).

## Tests added and what they cover

| Test file                                       | Coverage                                                                                                                                                       |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/features/search/recent-searches.test.ts`   | Empty start, newest first, case-insensitive dedupe, ignores short terms, keeps only the latest 5.                                                              |
| `src/features/search/useDebouncedValue.test.ts` | Value changes only after the delay, and a new value restarts the timer.                                                                                        |
| `src/features/search/SearchScreen.test.tsx`     | Empty submit shows the hint and does not navigate, typed text opens `/products?q=` and is saved, trimming, recent search press, hint after the debounce delay. |
| `src/__tests__/app/home-route.test.tsx`         | The Home search button opens `/search`.                                                                                                                        |

The last verified run on a local test branch with `mobile/mob-07` merged reported **17 suites and
80 tests passing**. On `mobile/mob-08` alone, `npm run check` passed in the pre-commit hook.
Jest prints a "worker process failed to exit gracefully" warning (a leaked timer); it is not a
failure.

## Run mobile checks

Use Node.js 22.13 or newer and run from `mobile/`:

```bash
cd mobile
npm ci
npm run check
```

Run the MOB-08 tests individually with:

```bash
npm test -- --runInBand src/features/search/recent-searches.test.ts
npm test -- --runInBand src/features/search/useDebouncedValue.test.ts
npm test -- --runInBand src/features/search/SearchScreen.test.tsx
npm test -- --runInBand src/__tests__/app/home-route.test.tsx
```

## Run and inspect the UI

`ProductList` is needed to see results. Create a throw-away local branch, merge MOB-07 into it,
and never push it:

```bash
git checkout -b test/mob-08-with-mob-07 mobile/mob-08
git merge mobile/mob-07
```

Then run the real backend as described in `MOB-07-PRODUCT-LIST.md` (seed data, API with
`--factory`, Wi-Fi IP in `mobile/.env`, `EXPO_PUBLIC_USE_MOCKS=false`) and start Expo:

```bash
npx expo start --lan --clear
```

What to check on the phone:

1. On Home, a "Search products" button appears under the scan button.
2. Tap it. The search screen opens.
3. Tap Search with an empty field. A hint appears and nothing opens.
4. Type `deodorant` and search. The product list opens with matching products.
5. Go back. `deodorant` appears under "Recent searches". Tap it to search again.
6. Tap a product card. The product screen opens.

Accent-insensitive search was checked against the real endpoint:

```bash
curl -s 'http://localhost:8000/api/v1/products/search?q=deodorant&limit=10'
```

It returned "Déodorant naturel" and two other products with "Déodorants" in the name. The local
database has no product named "Crème", so the "creme" finds "Crème" example from the task was
not tested with that exact word.

## Main files

| File                                       | Purpose                       |
| ------------------------------------------ | ----------------------------- |
| `src/features/search/recent-searches.ts`   | Recent searches storage       |
| `src/features/search/useDebouncedValue.ts` | Debounce hook                 |
| `src/features/search/SearchScreen.tsx`     | Search screen                 |
| `src/app/search.tsx`                       | `/search` route               |
| `src/features/home/HomeScreen.tsx`         | Home "Search products" button |
| `src/i18n/en.json`, `src/i18n/fr.json`     | `search.*` strings            |

## Pre-push checklist

- [ ] `mobile/npm run check` passes.
- [ ] `en.json` and `fr.json` have identical keys.
- [ ] `.env` files remain local and are not staged; no public environment variable contains a
      secret.
- [ ] Search was checked on a phone against the real backend, on a local test branch with
      `mobile/mob-07` merged.
- [ ] The test branch is never pushed. Push only `git push -u origin mobile/mob-08`.
- [ ] The PR is opened against `main`, and its description says that `ProductList` and
      `/products?q=` come from PR #36.
- [ ] Known limit understood: text query and category cannot be combined on the real backend yet.
