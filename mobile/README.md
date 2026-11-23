# DermaScan Mobile

React Native (Expo) app — the presentation layer for the DermaScan skincare platform. Talks to the FastAPI/PostgreSQL backend in `../backend` or the deployed cloud backend.

## Stack

- **Framework**: React Native 0.88 / Expo SDK 58 / Expo Router (file-based routing)
- **UI**: HeroUI Native + Uniwind (Tailwind CSS for React Native) + Lucide icons
- **State**: Zustand (session) + React Query (server cache)
- **Forms**: React Hook Form + Zod validation
- **Auth**: SecureStore (native) / memory-only (web); serialized token refresh
- **i18n**: i18next + react-i18next + expo-localization (English & French with dynamic locale headers)
- **Testing**: Jest 30 + jest-expo + React Native Testing Library
- **Contract**: OpenAPI TypeScript type synchronization (`npm run api:generate`)
- **Lint / Format**: oxlint + oxfmt
- **Types**: TypeScript 6 (strict)

## One-time setup

```sh
cd mobile
npm install
Copy-Item .env.example .env   # On macOS/Linux: cp .env.example .env
npx expo start
```

### Pointing the app at the backend

By default, the app is configured for **local backend development**:

- Default API URL: `http://localhost:8000`
- The client automatically appends `/api/v1` to the origin URL.

To customize your target backend, edit `.env`:

| Environment                             | Setting in `.env`                                                                                      |
| :-------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| **Local backend (Web / iOS Simulator)** | Default (`http://localhost:8000`)                                                                      |
| **Android Emulator**                    | `EXPO_PUBLIC_API_URL=http://10.0.2.2:8000`                                                             |
| **Physical Phone (Wi-Fi)**              | `EXPO_PUBLIC_API_URL=http://<YOUR_LAN_IP>:8000`                                                        |
| **Deployed Cloud Backend (Render)**     | `EXPO_PUBLIC_USE_CLOUD_BACKEND=true`<br>_or_ `EXPO_PUBLIC_API_URL=https://dermascan-iorj.onrender.com` |
| **Offline Mocks**                       | `EXPO_PUBLIC_USE_MOCKS=true`                                                                           |

> [!NOTE]
> All `EXPO_PUBLIC_*` variables are embedded into client bundles at build time. Never place secrets or private keys in `.env`.

## Scripts

| Script                 | Description                                                       | When to use                                                            |
| :--------------------- | :---------------------------------------------------------------- | :--------------------------------------------------------------------- |
| `npm run check`        | **Complete Quality Gate**: typecheck + lint + format:check + test | Before opening a PR or merging mobile changes                          |
| `npm test`             | Run Jest unit and integration tests                               | When changing behavior or debugging a failing test                     |
| `npm run typecheck`    | TypeScript type check (`tsc --noEmit`)                            | While developing typed code or investigating type errors               |
| `npm run lint`         | oxlint (type-aware linting)                                       | After changing JavaScript/TypeScript code or before a PR               |
| `npm run format`       | oxfmt (autofix formatting)                                        | To automatically format files after editing                            |
| `npm run format:check` | oxfmt (check formatting only)                                     | To verify formatting without modifying files                           |
| `npm run api:generate` | Export backend OpenAPI schema and generate TypeScript types       | After backend API changes that affect the mobile contract              |
| `npm run api:types`    | Regenerate TypeScript schema from `openapi.json`                  | After updating `openapi.json` without regenerating it from the backend |
| `npm run export:web`   | Expo web export                                                   | To create a static web build for preview or deployment                 |
| `npm run build:pwa`    | Web export + Workbox service worker                               | To create the installable/offline-capable production PWA build         |
| `npm run expo-check`   | Verify Expo SDK dependency alignment                              | After changing Expo dependencies or upgrading the Expo SDK             |

## Implemented routes

- `/`: paginated top-rated/recent shelves, search, categories, filters
- `/categories`, `/product/[id]`, `/scan`: category tree, ingredient/score details, barcode lookup
- `/account`, `/profile`, `/avoidance`: auth, skin profile, avoided products
- `/routines`, `/routine/add`, `/recommendations`: routine CRUD, conflicts, recommendations
- `/analysis`, `/contribute`: label OCR analysis and product submission

## Backend compatibility & migration

- `CUTOVER.md`: Migration and cutover runbook for production rollout.
- `docs/accessibility-checklist.md`: Device-level accessibility and quality checklist.
- `utils/apply_backend_fixes.py`: Reviewed backend patches.
- `utils/backend-tests/`: Backend contract regression tests.
