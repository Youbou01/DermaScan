# AGENTS.md: rules for AI coding assistants working in `mobile/`

Read this before writing or changing code here. Humans: the same rules apply to you.

## What this app is

A consumer app: scan a skincare product's barcode, see how its ingredients rate. The backend
(`../backend`, FastAPI) is the source of truth. The app never decides a score or a rating, it only
displays what the API returns.

## Stack (decided, do not swap without an ADR in `../docs/adr/`)

Expo SDK 58 (React Native 0.88, new architecture only) · TypeScript strict · Expo Router ·
TanStack Query · API client generated from the backend's `/openapi.json` (`openapi-typescript` +
`openapi-fetch`) · i18next + expo-localization (FR/EN, RTL-ready) · `expo-camera` for scanning ·
jest-expo + Testing Library · ESLint (flat) + Prettier. Package manager: **npm**.

## Your training data is older than this stack

Expo SDK 58 shipped on 2026-10-15. Do not trust memory for Expo, Expo Router or React Native
APIs. Check `https://docs.expo.dev/versions/v58.0.0/` (and the Expo Router docs) before using an
API, and prefer the code already in this repo over what you remember. If a snippet from the web
targets an older SDK, it is probably wrong here.

## Commands (run from `mobile/`)

- `npm run check` = typecheck + lint + format check + tests. **Must pass before every commit.**
- `npm run format` fixes formatting. `npm test` runs tests. `npm start` runs the dev server.
- Install Expo-managed packages with `npx expo install <pkg>` (picks the version matching the SDK),
  never `npm install <pkg>`. After touching dependencies run `npx expo-doctor`.

## Folder structure

```
src/
  app/          Expo Router routes ONLY. Thin: render a screen from features/, nothing else.
  features/     One folder per feature (scan, product, home, search, ...):
                  components/  hooks/  <feature>.types.ts  *.test.ts(x)
  components/   Shared, feature-agnostic UI: the design system (RiskBadge, Screen, ...).
  api/          Generated client + query hooks + mocks. The only code that talks to the network.
  i18n/         i18next setup and translation files (fr, en).
  theme/        Design tokens (colors, spacing, typography), light and dark.
  config/       env.ts: the ONLY place that reads environment variables.
  lib/          Small pure helpers (no React, no I/O).
  __tests__/    Tests of route files (they cannot live in src/app).
```

Imports use the alias `@/` (= `src/`). A feature never imports another feature's internals; share
through `components/` or `lib/`.

## Hard rules

1. **No `any`.** Use the generated API types; use `unknown` and narrow when a type is truly open.
   No `@ts-ignore`; `@ts-expect-error` only with a written reason.
2. **Type every function signature**, including explicit return types (React components return
   `ReactElement`). Lint enforces it.
3. **Thin screens.** A route file or screen component composes things. Logic goes in hooks, pure
   helpers in `lib/`, display in components.
4. **Nothing but routes in `src/app/`.** Expo Router turns every file there into a route, tests and
   helpers included. Default exports are only for route files.
5. **Never hand-write API types or URLs.** They come from the generated client. If the backend
   contract is missing something, say so, do not guess a shape.
6. **Environment:** read config only through `@/config/env`. `process.env.EXPO_PUBLIC_*` is
   embedded in the app and public: **never put a secret, key or credential in the app.**
7. **Server state** (anything from the API) lives in TanStack Query, not in `useState`/`useEffect`.
8. **No hard-coded user-visible text** once i18n exists (MOB-03): every string goes through
   i18next. Never concatenate translated fragments; use interpolation.
9. **Handle every state:** loading (skeleton), empty, error (with retry), and the success path.
   Treat every optional field in the API as possibly missing.

## Product rules (these are safety and trust rules, not style)

- **Colour is never the only signal.** A risk level is always colour + icon + text label, and a
  screen reader announces it. Use `RiskBadge`; do not render a risk level any other way.
- **`unknown` is never green** and never shown as safe. "Insufficient data" is a state of its own.
- **Wording:** "risk indicator" / "concern level". Never "safe", "unsafe", "toxic", "harmful".
- The API returns semantic values (`low | moderate | high | unknown`); the app maps them to
  colour, icon and label in one place.
- Touch targets are at least 44x44 pt. Text must survive large-font settings. Respect dark mode.
- Branch on error `type` (e.g. `urn:skincare:problem:product-not-found`), never on `detail` text.

## Testing

- Colocate tests: `thing.ts` next to `thing.test.ts` (route tests go in `src/__tests__/app/`).
- Test behaviour the user sees (Testing Library queries by text/role/label), not implementation.
- Logic in `lib/` and hooks gets unit tests. A bug fix includes a test that failed before.

## Definition of done

`npm run check` green · every state handled · tested · accessible (labels, roles, 44 pt) ·
no new dependency without a reason · PR includes a screen recording from a real device.
