# Design system team check (Windows / PowerShell)

## Install and open

```powershell
cd mobile
npm ci
npx expo install --check
npx expo-doctor
npm start
```

Open the app with the matching Expo Go version or a simulator/emulator. From the home screen, tap **Design system** (development builds only). No backend is needed; examples are local and illustrative.

## What to inspect

1. **RiskBadge:** check Low, Moderate, High, and Not enough data. Toggle grayscale; each must still have a different icon and readable label. Inspect the compact badge with VoiceOver/TalkBack; its full label should be announced once.
2. **ScoreBadge:** check scores across the bands and the absent/unknown score. The unknown state must not look favorable; screen readers should announce the score out of 100 and its band.
3. **ProductCard:** inspect long names, missing and broken-image placeholders, missing brand, score, risk, pressed feedback, and its single combined accessible label. Activate it with a screen reader.
4. **Screen:** confirm safe content edges on a notched iPhone and small Android screen; scroll and pull to refresh when a callback is connected.
5. **Skeleton:** check block, line, and product-card forms. Turn on the device's Reduce Motion setting; placeholders should remain static.
6. **ErrorState:** try generic, no-connection, and server-problem variants; retry must be reachable and activate once. Confirm no raw error text appears.
7. **EmptyState:** check localized title/message and optional action.
8. Increase system text size. Content should wrap and remain usable without clipped fixed-height text. Switch device language between English and French to verify UI localization.

## Run checks

```powershell
npm run check
```

This runs TypeScript, ESLint, Prettier, and Jest. If Expo cannot resolve a module, run `npx expo install --check` and `npx expo-doctor`; restart with `npx expo start --clear` after config changes. Expo Go can lag a new SDK; follow the SDK 58 options documented in `mobile/README.md`.
