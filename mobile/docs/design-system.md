# Mobile design system

## Theme tokens

`src/theme/theme.tsx` exports typed `ThemeProvider`, `useTheme()`, and light/dark token sets. The system appearance selects the palette. Values are density-independent points.

| Group                 | Tokens                                                                                                                       |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Brand and surfaces    | Primary `#2457D6`; light background `#F5F7FC`; surface `#FFFFFF`; text `#17233B`; secondary text `#52627D`; border `#D8DFEC` |
| Dark surfaces         | Background `#101827`; surface `#1A2638`; text `#F3F6FC`; secondary text `#C1CCDE`; primary `#91AEFF`                         |
| Spacing               | 4, 8, 16, 24, 32                                                                                                             |
| Radius                | 10, 16, 24, pill (999)                                                                                                       |
| Typography            | Caption 13/18, body 16/24, title 24/32, score 28/36 (font size/line height); regular 400, medium 600, bold 700               |
| Icons and interaction | 16, 20, 28; minimum target 44x44                                                                                             |
| Elevation             | Card 2, raised 4                                                                                                             |

Risk semantic colors include a foreground, background tint, border, and icon. Measured foreground/background contrast for risk labels is:

| Backend value | User label       | Icon | Light foreground / tint | Light contrast | Dark foreground / tint | Dark contrast |
| ------------- | ---------------- | ---- | ----------------------- | -------------: | ---------------------- | ------------: |
| `low`         | Low concern      | ✓    | `#17613B` / `#E5F4EA`   |         6.57:1 | `#A9E4BC` / `#193B2B`  |        8.53:1 |
| `moderate`    | Moderate concern | −    | `#754600` / `#FFF1D6`   |         7.14:1 | `#FFDA91` / `#493517`  |        8.69:1 |
| `high`        | High concern     | ▲    | `#922D28` / `#FCE9E7`   |         6.83:1 | `#FFB4AC` / `#4A2527`  |        7.81:1 |
| `unknown`     | Not enough data  | ?    | `#394A67` / `#E9EDF4`   |         7.61:1 | `#D4DCEE` / `#2B374A`  |        8.74:1 |

All listed pairs exceed WCAG AA's 4.5:1 body-text threshold. The automated contrast test also checks primary and secondary text against each mode's background. `unknown` is always separate from favorable and never means safe.

## Components

```tsx
<RiskBadge level="moderate" />
<ScoreBadge score={72} band="moderate" />
<ProductCard name="Dew Veil" brand="Mora" score={72} scoreBand="moderate" onPress={openProduct} />
<Screen title="Products" onRefresh={refresh} refreshing={isRefreshing}>{children}</Screen>
<Skeleton variant="product" reduceMotion />
<ErrorState variant="offline" onRetry={reload} />
<EmptyState actionLabel="Browse" onAction={browse} />
```

- `RiskBadge`: backend `low | moderate | high | unknown`; always shows symbol and localized label, with one screen-reader label. `compact` hides visual text but keeps an accessible label.
- `ScoreBadge`: score plus the backend concern band; missing score/`unknown` means insufficient data.
- `ProductCard`: pressable list row with name, optional brand/category/image, score/risk. Missing or broken images use a placeholder; long names wrap to two lines.
- `Screen`: safe area, themed background, optional scroll, keyboard avoidance, title, and pull-to-refresh.
- `Skeleton`: block, line, or product-card placeholder. Pass `reduceMotion` when reduced motion is enabled.
- `ErrorState`: localized generic, offline, or server error with retry. Raw error details are not displayed.
- `EmptyState`: localized empty-list/search state and optional action.

Visible component copy comes from i18next resources in `src/i18n/strings.ts`; `expo-localization` selects English or French from device preferences. Text uses scalable native fonts without fixed-height text containers. Give every interactive element a 44pt minimum target and never rely on color alone to communicate concern.

## Showcase

Start the app with `npm start`, then tap **Design system** on the home screen in development. The `/showcase` route redirects home in production. It uses local illustrative data and makes no network calls. Toggle grayscale to check that symbols and labels remain clear.
