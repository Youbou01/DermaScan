# ADR-0010: Mobile stack
- Status: Accepted
- Date: 2026-10-19

## Context
Nobody on the team has shipped React Native, and much of the code is AI-assisted. The app must
feel like a professional daily-use app (scanning, fast lists, accessibility) and must stay in sync
with a backend whose OpenAPI schema is already the contract (ADR-0007).

## Decision
- **Expo** (managed workflow, native folders generated, never committed) with **Expo Router**,
  **TypeScript strict**, **npm**. **SDK 58** (React Native 0.88): the newest release on the day we
  started, so there is no upgrade to do right after day one.
- **Server state:** TanStack Query. **API client:** generated from `/openapi.json` with
  `openapi-typescript` + `openapi-fetch`, so a backend change that breaks the app is a type error.
- **i18n:** i18next + expo-localization, FR/EN, RTL-ready (ADR-0006: the API returns codes, the app
  owns its own UI strings). **Scanning:** `expo-camera`.
- **Quality:** ESLint (flat) + Prettier, jest-expo + Testing Library, one gate `npm run check`
  run by pre-commit and CI. `mobile/AGENTS.md` gives AI assistants the same rules.

## Consequences
- **Expo Go lags a new SDK.** The store version of Expo Go moves to SDK 58 a few weeks after the
  release; until then iPhones need `eas go` or a development build. Expo Go is also only a preview
  tool: native code, camera permissions copy and release builds need **development builds**.
  Plan to adopt them before the first beta.
- **SDK upgrades are deliberate PRs** (`npx expo install expo@^NN --fix`), never Dependabot bumps
  of single packages.
- **Nothing secret in the app.** `EXPO_PUBLIC_*` values ship inside the bundle. Any key or
  credential belongs to the backend.
- **Production API must be HTTPS** (release builds block cleartext HTTP).
- AI assistants know this SDK poorly: `AGENTS.md` tells them to read the v58 docs first.
