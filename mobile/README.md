# Skincare mobile app

Expo (React Native) + TypeScript. Talks to the FastAPI backend in `../backend`.
Rules for contributors and AI assistants: [`AGENTS.md`](AGENTS.md).
Why this stack: [ADR-0010](../docs/adr/0010-mobile-stack.md).

## One-time setup

Requirements: Node.js **22.13 or newer**, and a phone or an emulator. The project rejects older
Node versions (`engine-strict=true` in `.npmrc`). Use your Node version manager to select Node 22 or
newer, then verify with `node --version`.

```bash
cd mobile
npm ci                      # installs exactly package-lock.json, replacing any stale node_modules
npx expo install --check    # verifies SDK-compatible package versions
npx expo-doctor             # health check, should report no problems
npm run check               # typecheck + lint + format check + tests
```

Copy `.env.example` to `.env`, then set `EXPO_PUBLIC_API_URL` (see below). In PowerShell, use
`Copy-Item .env.example .env`; in macOS/Linux shells, use `cp .env.example .env`.

**Commit `package-lock.json`** with every dependency change; contributors and CI use `npm ci`,
which requires the lockfile and installs its exact versions.
The pre-commit hooks (installed once with `cd backend && uv run pre-commit install`, see
CONTRIBUTING) run `npm run format` and `npm run check` on every commit that touches `mobile/`.

## Run the app

```bash
npm start       # shows a QR code; press a / i for an emulator or simulator
```

### Open it on a real phone: read this, SDK 58 is new

Expo SDK 58 was released on 2026-10-15. The App Store / Google Play version of **Expo Go**
supports only one SDK at a time and moves to SDK 58 "within a few weeks" of that date. Until it
does, pick one:

- **Android:** `npm start` installs the matching Expo Go on a connected device or emulator.
- **iPhone:** use `eas go` (needs a free Expo account) or a development build.
- **Or wait** for the store version of Expo Go to reach SDK 58.
- Expo Go now requires you to be logged in, in both the terminal (`npx expo login`) and the app.

Expo Go is a learning and preview tool. Anything native we add later and a release build need a
**development build** (`npx expo run:ios|android` or EAS Build).

### Pointing the app at the backend

Set `EXPO_PUBLIC_API_URL` in `.env` to the backend root **without** `/api/v1`:

| Where the app runs           | Value                                  |
| ---------------------------- | -------------------------------------- |
| Real phone on the same Wi-Fi | `http://<your computer's LAN IP>:8000` |
| Android emulator             | `http://10.0.2.2:8000`                 |
| iOS simulator                | `http://localhost:8000`                |

`localhost` on a real phone is the phone itself. Start the backend so it listens on all
interfaces (`uvicorn ... --host 0.0.0.0`). `EXPO_PUBLIC_USE_MOCKS=true` runs without a backend
(fixtures arrive with MOB-02). Production must be `https://`: release builds block plain `http://`.

## Scripts

| Script                                                            | What it does                                               |
| ----------------------------------------------------------------- | ---------------------------------------------------------- |
| `npm run check`                                                   | typecheck + lint + format check + tests (the quality gate) |
| `npm run typecheck` / `lint` / `format` / `format:check` / `test` | the individual steps                                       |
| `npm start` / `android` / `ios`                                   | dev server                                                 |

## Troubleshooting

- **`npm install` complains about peer dependencies, or jest cannot start:** run
  `npx expo install --fix`, then `npx expo-doctor`. The test stack (Jest 30, jest-expo,
  `@react-native/jest-preset`, Testing Library) must be on the versions the installed Expo SDK
  expects; if a message names a missing peer such as `react-test-renderer`, install the one it names.
- **Types error about `expo/tsconfig.base.json`:** run `npm install` first (the file ships in the
  `expo` package).
- **Phone cannot reach the API:** wrong `EXPO_PUBLIC_API_URL`, backend not bound to `0.0.0.0`, or a
  firewall. Open the URL in the phone's browser to check. Restart `npm start` after editing `.env`.
- **A change to `.env` is ignored:** `EXPO_PUBLIC_*` is inlined into the bundle: restart with
  `npx expo start --clear`.
