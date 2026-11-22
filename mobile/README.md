# DermaScan Mobile

React Native (Expo) app — the replacement presentation layer for the DermaScan FastAPI/PostgreSQL backend.

## Stack

- **Framework**: React Native 0.88 / Expo SDK 58 / Expo Router (file-based routing)
- **UI**: HeroUI Native + Uniwind (Tailwind CSS for React Native) + Lucide icons
- **State**: Zustand (session) + React Query (server cache)
- **Forms**: React Hook Form + Zod validation
- **Auth**: SecureStore (native) / memory-only (web); serialized refresh
- **Analytics**: PostHog (web only, opt-in via query params)
- **Lint / Format**: oxlint + oxfmt
- **Types**: TypeScript 6 (strict)

## Quick start

```sh
cd mobile
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_URL` to override the default API origin (`https://dermascan-iorj.onrender.com`).
The variable takes the **origin only** — `/api/v1` is appended by the client.

## Scripts

| Script                 | Description                                  |
| ---------------------- | -------------------------------------------- |
| `npm run lint`         | oxlint (type-aware)                          |
| `npm run format`       | oxfmt (autofix)                              |
| `npm run format:check` | oxfmt (check only)                           |
| `npm run typecheck`    | TypeScript type check                        |
| `npm run check`        | All quality gates: typecheck + lint + format |
| `npm run export:web`   | Expo web export                              |
| `npm run build:pwa`    | Web export + Workbox service worker          |
| `npm run expo-check`   | Verify Expo SDK dependency alignment         |

## Implemented routes

- `/`: paginated top-rated/recent shelves, search, categories, filters
- `/categories`, `/product/[id]`, `/scan`: category tree, ingredient/score details, barcode lookup
- `/account`, `/profile`, `/avoidance`: auth, skin profile, avoided products
- `/routines`, `/routine/add`, `/recommendations`: routine CRUD, conflicts, recommendations
- `/analysis`, `/contribute`: label OCR analysis and product submission

## Backend compatibility

The `utils/` directory contains:

- `apply_backend_fixes.py`: reviewed backend patches (estimated-score metadata, localized search, contribution upload validation)
- `backend-tests/`: regression tests to port into the backend CI

See `CUTOVER.md` for the full migration runbook.
