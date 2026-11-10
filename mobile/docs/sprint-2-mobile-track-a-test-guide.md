# Sprint 2 Mobile Track A — How to test it

Run the app and checks from Windows PowerShell. This guide covers MOB-S2-1 through MOB-S2-4. Auth, profile, and suitability remain fixture-backed until their backend endpoints are added to OpenAPI. Product-level AI summary is deferred until its field and translation namespace are agreed.

## 1. Install and run the mobile app

```powershell
cd C:\Users\dunno\Desktop\fs\dermaScan\DermaScan\mobile
npm ci
npx expo install --check
npx expo-doctor
npm run check
```

Start the app and scan its QR code with Expo Go on the same Wi-Fi:

```powershell
npm start
```

If the phone cannot reach the development server, use a tunnel:

```powershell
npx expo start --tunnel
```

For an Android emulator with Android Studio installed and an emulator already running:

```powershell
npm run android
```

Expo SDK 58 needs a matching Expo Go version. If the store app has not received SDK 58, use a compatible development build or the Android emulator option described in `mobile/README.md`.

## 2. Run without a backend (mock mode)

Create or replace `.env` in `mobile/`:

```powershell
@"
EXPO_PUBLIC_USE_MOCKS=true
"@ | Set-Content -Encoding utf8 .env
npx expo start --clear
```

Expected results:

1. The home feed and category tiles load from fixtures.
2. Tap a category; `/products` opens with that category selected. Search for `serum`, choose concern bands, and add/remove include or avoid ingredient tags. Tap a result to open product details.
3. Create an account with a valid email, a password of at least 8 characters, and a name. The session is restored after restarting the app. In the same app session, trying to register that email again shows a duplicate-account message.
4. Sign out, then sign in with the fixture account `demo@dermascan.app` / `DermaScan123!`. An incorrect password shows an authentication error.
5. Open **My Profile**. Change skin type, pregnancy/nursing, health conditions, and allergy IDs. Allergy input accepts a UUID because the agreed profile contract contains ingredient IDs and the backend has no ingredient lookup endpoint yet. Remove the sample blacklisted cleanser with one tap.
6. Open the **Gentle Cream Cleanser** detail to see the fixture-backed blacklist warning and suitability alert. Other fixture products use the default suitable verdict. Product cards include risk icon/label badges.

The mock account directory is in memory for the current app process; only the signed-in session is persisted. Profile updates use the shared mock profile fixture.

## 3. Run against the live backend

Set a backend root URL (without `/api/v1`) and disable mocks. For an Android emulator:

```powershell
@"
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000
EXPO_PUBLIC_USE_MOCKS=false
"@ | Set-Content -Encoding utf8 .env
npx expo start --clear
```

For iOS Simulator, use `http://localhost:8000`. For a physical phone, use the computer’s LAN IP (for example `http://192.168.1.20:8000`) and keep both devices on the same Wi-Fi.

If the backend has not been started yet, the repository’s local setup from PowerShell is:

```powershell
cd ..\backend
uv sync
Copy-Item .env.example .env
docker compose up -d db
uv run alembic upgrade head
uv run python scripts/seed_demo.py
uv run uvicorn app.main:create_app --factory --reload --host 0.0.0.0
```

Then in another PowerShell window return to `mobile/` and start Expo. The backend commands above are for local development; they were not run as part of this mobile task.

Expected live behavior with the current backend contract:

1. Product search uses `GET /api/v1/products/search` with `q`, `limit`, and `cursor`.
2. Category, band, include, and exclude filters use `GET /api/v1/products/filter` with `category`, `band`, `include`, `exclude`, `limit`, and `cursor`. When text and filters are combined, the app intersects the two endpoint result pages.
3. Product detail uses the existing product endpoint.
4. Auth, profile, blacklist, and suitability show a clear unavailable message because those endpoints are not in the current OpenAPI schema. Switch to mock mode to exercise those flows.

Restart Expo with `npx expo start --clear` after changing `.env`; Expo embeds `EXPO_PUBLIC_*` values in the app bundle.

## 4. Negative, edge, and accessibility checks

1. **Credentials:** submit an invalid email, a password shorter than 8 characters, a blank name, a wrong password, and a duplicate email during the same app session. Confirm the relevant inline message appears and invalid fields do not submit.
2. **Search:** search for a name with no matches; clear all text; try an unknown category slug; add and remove include/avoid tags; select and clear risk bands. Confirm the empty state appears for no matches and the retry control appears on a simulated network error.
3. **Network failure:** in live mode stop the backend or use an invalid API host. Search should show an error state with a retry button. Auth/profile/suitability should identify that their live contract is unavailable.
4. **French:** clear app data or reinstall so the saved language preference is removed, set French as the device language, then relaunch. Confirm category names, search controls, profile labels, and suitability labels are French. A previously saved language preference takes precedence over the device language.
5. **Large text:** enable the largest system text size. Scroll each screen and confirm titles, chips, inputs, buttons, and alerts remain visible and usable.
6. **Screen reader:** use VoiceOver or TalkBack. Confirm fields and controls have names, category and filter chips announce selection, risk badges announce icon-independent concern labels, and errors/empty states can be read.
7. **Grayscale and dark mode:** inspect risk badges and suitability alerts without color. Confirm their icon and text still communicate the concern level in light and dark appearance.

## 5. Common problems

- **Node version error:** use Node.js 22.13 or newer, then rerun `npm ci`.
- **Expo Go SDK mismatch:** use an SDK 58 compatible Expo Go/development build, or use the Android emulator.
- **Phone cannot connect to Expo:** use `npx expo start --tunnel`; the phone needs internet access for the tunnel.
- **Phone cannot connect to backend:** do not use `localhost` on a phone. Use the computer’s LAN IP, bind Uvicorn to `0.0.0.0`, and check the firewall.
- **Environment change has no effect:** restart with `npx expo start --clear`.
- **`expo-doctor` cannot download:** check network access and retry; it is invoked through `npx` and may need to fetch the tool.
- **`npm run check` formatting failure:** the current checkout has existing Prettier failures in `app.json`, `openapi.json`, `package.json`, `src/app/scan.tsx`, `src/features/scan/ScanScreen.tsx`, and `MOB-04-SCANNER.md`. The scanner files belong to Developer 4 and are left untouched here.
