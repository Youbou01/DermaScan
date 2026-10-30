# MOB-03 Internationalization: Implementation and Test Guide

This document records the English/French localization layer, category-name behavior, and ways to
run and verify it on a device.

## What was added

- **i18next setup:** `src/i18n/i18n.ts` registers English (`en`) and French (`fr`) resources with
  typed translation keys and English fallback.
- **Device locale detection:** `src/i18n/language-state.ts` reads the preferred locale through
  `expo-localization`. French locales select French; other locales select English.
- **Language provider and persistence:** `src/i18n/LanguageProvider.tsx` restores a saved
  `en`/`fr` preference from AsyncStorage, exposes `useLanguage()` with `currentLanguage`,
  `setLanguage()`, and `isRTL`, and delays route rendering until initialization finishes. A storage
  failure falls back to the detected device language; language changes still apply in the current
  session if saving fails.
- **Visible language control:** The placeholder home screen has English and French buttons. The
  selection updates the app immediately and is saved for the next launch.
- **Translation dictionaries:** `src/i18n/en.json` and `src/i18n/fr.json` contain common actions,
  errors, risk labels and screen-reader announcements, the development showcase copy, and category
  names keyed by the backend's stable slugs.
- **Category resolver:** `getLocalizedCategory()` in `src/i18n/category.ts` returns a non-empty
  translated category name when the slug is known; otherwise it returns the API `name`. Product
  cards receive only a category slug, so they show a localized label for known slugs and omit an
  unknown slug rather than displaying machine-formatted text.
- **API locale bridge:** `src/api/locale.ts` exposes the active language to the API client. Its
  request middleware sends that value in `Accept-Language`.
- **Expo configuration:** `app.json` declares English and French as supported locales and enables
  RTL readiness through `expo-localization`. The currently supported app languages are both LTR.

## Category slugs

Category keys follow `backend/src/app/modules/ingestion/data/categories.json`:

`face-care`, `cleanser`, `toner`, `serum`, `moisturizer`, `face-mask`, `exfoliant`, `eye-care`,
`sun-care`, `sunscreen`, `after-sun`, `body-care`, `body-lotion`, `body-wash`, and `lip-care`.

Use the backend slug as the dictionary key. Do not pluralize or otherwise transform it. API names
remain the fallback for categories added by the backend before the mobile dictionaries are updated.

## Run the app and inspect the UI

From the repository root:

```bash
cd mobile
npm ci
npx expo start --lan
```

Scan the Expo CLI QR code with Expo Go on a phone connected to the same Wi-Fi. The project targets
iOS and Android; there is no web app configured. Use an Expo Go version compatible with SDK 58, or
run a matching development build if the store version is not yet compatible.

On the home screen:

1. Tap **English** or **Français**. The selected option is marked, and the development showcase
   link changes language.
2. Open the design system showcase to inspect the translated risk badges, score labels, and error
   and empty states.
3. Close and reopen the app. The selected language should remain active.

To check automatic device detection, clear the app's saved data (or reinstall it), set the device
preferred language to French, and relaunch. French should be selected. With any non-French device
locale, the initial language should be English. A previously saved manual choice takes precedence
over the device locale.

The showcase uses local sample data. API screens require a configured backend as described in
`README.md`; API requests already send the selected language in `Accept-Language`.

## Automated tests

Run the full mobile quality gate from `mobile/`:

```bash
npm run check
```

This runs TypeScript (`tsc --noEmit`), ESLint, Prettier check, and Jest. The MOB-03 verification
reported **10 suites and 42 tests passing**.

Focused i18n tests can be run individually:

```bash
npm test -- --runInBand src/i18n/language-state.test.ts
npm test -- --runInBand src/i18n/LanguageProvider.test.tsx
npm test -- --runInBand src/i18n/category.test.ts
npm test -- --runInBand src/i18n/dictionaries.test.ts
npm test -- --runInBand src/api/api.test.ts
```

Coverage includes French device detection and the English fallback, language changes and storage
restoration, category translation and API-name fallback, identical dictionary key structures, the
translated home-screen control, and the `Accept-Language` request header. `npx expo-doctor` also
passed all 20 project checks after the localization dependencies were added.

## Main files

| File                                   | Purpose                                           |
| -------------------------------------- | ------------------------------------------------- |
| `src/i18n/en.json`, `src/i18n/fr.json` | English and French dictionaries                   |
| `src/i18n/i18n.ts`                     | Typed i18next initialization                      |
| `src/i18n/language-state.ts`           | Device locale detection and active locale getter  |
| `src/i18n/LanguageProvider.tsx`        | Startup, `useLanguage()`, and persisted switching |
| `src/i18n/category.ts`                 | Category translation and fallback helpers         |
| `src/api/locale.ts`                    | Active language exposed to API requests           |
| `src/app/index.tsx`                    | Home-screen language control                      |
| `src/app/_layout.tsx`                  | App-wide language provider                        |
