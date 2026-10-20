# MOB-01 Design System

## Purpose and scope

MOB-01 establishes the mobile app's first shared visual foundation: typed theme tokens, accessible
display and state components, and a development-only showcase. The components use React Native
`StyleSheet`; no styling framework or icon dependency was added.

The showcase is a UI demonstration. It does not make API requests or compute product scores. The
backend remains the source of truth for scores and risk levels; the mobile layer displays the
semantic values supplied by the generated API contract.

## What was added

### Theme tokens

`src/theme/tokens.ts` exports:

- Light and dark semantic colors for backgrounds, surfaces, text, borders, primary actions, risk
  levels, and loading placeholders.
- Typed typography scales for sizes, line heights, weights, and letter spacing.
- Shared spacing and corner-radius scales.
- `useThemeColors()`, which selects the light or dark palette from the operating-system color
  scheme. The token shape can be extended for future high-contrast or app-selected themes.

### Components

All components are exported from `src/components/index.ts` and can be imported from
`@/components`.

| Component     | Behavior                                                                                                                                                                                                                                                                            |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RiskBadge`   | Displays `low`, `moderate`, `high`, or `unknown` as a color-tinted badge with a distinct glyph and explicit text. Its grayscale preview removes risk colors while keeping the shape and label. It exposes a full `accessibilityLabel`. Unknown is presented as “Insufficient data.” |
| `ScoreBadge`  | Displays a numeric score out of 100, or “Insufficient data” when the score is null/unknown. Uses the score band when provided and otherwise derives a display tier from the score. Announces the score and maximum to assistive technology.                                         |
| `ProductCard` | Pressable product row with product name, brand fallback, optional category slug, score/risk badge, and product image. Null or failed image loads show a placeholder. Calls `onPress(product.id)` when activated.                                                                    |
| `Screen`      | Safe-area wrapper with a scrollable, keyboard-avoiding layout by default, or a fixed-height layout with `scroll={false}`.                                                                                                                                                           |
| `Skeleton`    | Accessible loading placeholder with `rect`, `circle`, and `text` variants; configurable dimensions/radius and a pulsing opacity animation.                                                                                                                                          |
| `ErrorState`  | Centered error presentation with icon, title, explanation, and an optional retry button. Title, description, label, and handler can be customized.                                                                                                                                  |
| `EmptyState`  | Centered empty presentation with icon, title, explanation, and an optional React-node action slot.                                                                                                                                                                                  |

Buttons and cards use accessible React Native pressables and meet the 44 pt minimum touch target.
Risk meaning is conveyed with text and glyph as well as color. System dark mode is supported through
the shared color hook.

### Showcase

Open the app in development mode and use **Open design system showcase** on the placeholder home
screen. The route is `src/app/design-system.tsx` and returns no screen in production builds.

The showcase displays all four risk values, a grayscale preview switch, score tiers, a short product
card and a long-name/missing-image card, skeleton variants, and interactive error/empty examples.
The retry, card, and empty-state actions show an on-screen status message.

## Files added or changed for MOB-01

| File                                    | Change                                                                                     |
| --------------------------------------- | ------------------------------------------------------------------------------------------ |
| `src/theme/tokens.ts`                   | Added light/dark color palettes, typography, spacing, radii, types, and color-scheme hook. |
| `src/components/RiskBadge.tsx`          | Added accessible semantic risk badge and grayscale option.                                 |
| `src/components/ScoreBadge.tsx`         | Added accessible numeric score badge and tier styling.                                     |
| `src/components/ProductCard.tsx`        | Added typed, pressable API product card and image fallback.                                |
| `src/components/Screen.tsx`             | Added safe-area, scroll, and keyboard-avoiding layout wrapper.                             |
| `src/components/Skeleton.tsx`           | Added configurable pulsing loading placeholder.                                            |
| `src/components/ErrorState.tsx`         | Added retryable error presentation.                                                        |
| `src/components/EmptyState.tsx`         | Added empty presentation with optional action slot.                                        |
| `src/components/index.ts`               | Added shared component and prop-type exports.                                              |
| `src/app/design-system.tsx`             | Added the development-only component showcase route.                                       |
| `src/app/index.tsx`                     | Added a development-only home-screen link to the showcase.                                 |
| `src/components/design-system.test.tsx` | Added unit tests for the shared primitives.                                                |

No package or lockfile change is required for MOB-01. There is no `@expo/vector-icons` dependency in
the current project, so the risk badges use text glyphs rather than introducing an icon package.
Visible component copy is currently English; connect it to i18next when MOB-03 adds the app's UI
localization provider.

## API and endpoint alignment

MOB-01 adds no endpoint and the showcase calls no endpoint. Component prop types come from the
generated `src/api/types.ts` aliases and `src/api/generated/schema.d.ts`:

- `RiskLevel` is `low | moderate | high | unknown`.
- `ProductCard` data uses `ProductCardOut`: `id`, `name`, nullable `brand`, nullable `image_url`,
  nullable `score` (0–100), nullable `score_band`, and nullable `category_slug`.
- `ProductDetail` also carries a `score_band`; the API describes `unknown` as insufficient data,
  never as safe.

Existing backend routes that can supply product data to these display components include:

| Existing method and path                    | Use                                                               |
| ------------------------------------------- | ----------------------------------------------------------------- |
| `GET /api/v1/home`                          | Loads home sections; section items can include product card data. |
| `GET /api/v1/home/sections/{section_id}`    | Loads additional items for a home section.                        |
| `GET /api/v1/products/{product_id}`         | Loads a product detail response.                                  |
| `GET /api/v1/products/by-barcode/{barcode}` | Loads a product after barcode scanning.                           |

These routes are already present in `mobile/openapi.json`; MOB-01 neither changes their contract nor
connects them to a screen. When wiring a real product list or detail screen, pass the generated API
data into `ProductCard`/`ScoreBadge` and `RiskBadge`; do not calculate or infer backend risk ratings
in the UI.

## Local setup and preview

Requirements and setup follow `mobile/README.md`: Node.js 22.13 or newer, npm, and Expo Go or an
emulator/device compatible with the project's Expo SDK.

From the repository root:

```bash
cd mobile
npm ci
npm run check
npx expo start --lan
```

Scan the Expo CLI QR code with Expo Go on a phone connected to the same Wi-Fi as the computer. The
app opens on the placeholder home screen; tap **Open design system showcase**. The route can also be
opened directly as `/design-system` in the Expo Router app.

The showcase uses local sample data and does not require a running backend or `.env` API URL. Other
API-backed screens still use `EXPO_PUBLIC_API_URL` and the existing environment setup described in
`mobile/README.md`. The project currently targets iOS and Android; web is not configured in
`app.json`.

## Tests and quality checks

Tests are colocated in `src/components/design-system.test.tsx` and use Jest with
React Native Testing Library. They verify:

- Each risk value renders its label, glyph identifier, and full accessibility label.
- Score badge accessibility reports the score and maximum.
- Product cards render product text and score, and presses call back with the product ID.
- `Screen` renders its content.
- Error retry invokes its handler.
- Empty state renders caller-provided actions.
- Skeleton accepts and applies width, height, and radius.

Run the repository's full mobile quality gate from `mobile/`:

```bash
npm run check
```

This runs `tsc --noEmit`, ESLint, Prettier check, and Jest. The MOB-01 implementation was verified
with this command: **6 suites and 34 tests passed**.
