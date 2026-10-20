# MOB-04 Barcode Scanner

This document summarizes the mobile frontend work completed for MOB-04.

## What was implemented

- Added a barcode scanning screen using `expo-camera`, supporting EAN-13, EAN-8, and UPC-A.
- Added camera permission handling, including a path to open device settings when permission is denied.
- Added torch control, scan debouncing, and protection against repeated scans of the same barcode.
- Added manual barcode entry as an alternative to using the camera.
- Looked up products through the existing mobile API query. A successful lookup opens the product details route; unknown products, invalid barcodes, and other request failures display translated feedback with retry where appropriate.
- Added a translated scanner entry point on the home screen and corrected its product link to use the existing `/products/[productId]` route.
- Added English and French translations for scanner controls, instructions, and feedback.
- Registered the Expo Camera plugin and its camera permission message in `app.json`; audio recording is disabled.
- Added the SDK-matched `expo-camera` dependency and updated the npm lockfile.

## Main files

| File                                   | Purpose                                                                                |
| -------------------------------------- | -------------------------------------------------------------------------------------- |
| `src/features/scan/ScanScreen.tsx`     | Scanner UI, camera permission, barcode handling, manual entry, and product lookup flow |
| `src/app/scan.tsx`                     | Thin Expo Router route for the scanner screen                                          |
| `src/features/home/HomeScreen.tsx`     | Home screen entry point to scanning and product route correction                       |
| `src/i18n/en.json`, `src/i18n/fr.json` | English and French scanner strings                                                     |
| `app.json`                             | Expo Camera plugin and permission configuration                                        |
| `package.json`, `package-lock.json`    | Expo Camera dependency                                                                 |

## Scope

All implementation changes were limited to the mobile frontend. No backend or migration files were changed. The existing API client, query, theme, and translation setup were reused.

## Verification and device setup

TypeScript, ESLint, and Prettier checks passed for the implementation; Expo Doctor reported all 20 checks passing. The scanner should also be exercised on a physical device with camera permission enabled.

From this directory, start Expo with:

```bash
npx expo start --lan
```

For an offline UI/demo run, configure `EXPO_PUBLIC_USE_MOCKS=true` in `mobile/.env`. For real product lookups, configure `EXPO_PUBLIC_API_URL` as described in `README.md` and make the backend reachable from the phone.
