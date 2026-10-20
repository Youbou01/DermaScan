# Mobile accessibility and polish audit

This checklist is the MOB-12 review record. A screen is signed off only after it has a real UI
implementation and each applicable check has been verified on device or in a representative
accessibility test. Placeholder routes stay pending; do not count an unimplemented check as a pass.

## Foundation review

The mobile API layer includes generated product types and TanStack Query detail hooks (MOB-02).
The shared `RiskBadge`, `ScoreBadge`, screen states, and theme tokens (MOB-01) are now present. The
MOB-05 product detail screen uses those shared components and tokens. The i18n setup (MOB-03) is
still pending, so product-detail copy is centralized temporarily for migration to the shared
translation resources when they land.

The current route files are still scaffolds. Source inspection can record semantic roles and
declared layout constraints, but it cannot verify rendered touch bounds, screen-reader output,
contrast, large-text layout, or RTL behavior. Those checks remain pending for device/accessibility
verification after the real screens land.

## Sign-off checks

For every screen, record **Pass**, **Fail**, or **N/A with a reason** for each applicable item.

- **Grayscale:** Meaning remains clear without color. Risk indicators include an icon and a text
  label as well as color; `unknown` is presented as insufficient data and never as a low-risk state.
- **Large text:** Increase the device text size to its largest supported setting. Text remains
  readable, controls remain usable, and content can scroll without clipping or overlap.
- **Touch targets:** Every interactive target is at least 44 by 44 pt, with enough separation to
  avoid accidental activation.
- **Screen reader:** Controls have useful accessible names and roles; reading order follows the
  visual order; dynamic loading, empty, error, and success states are announced when relevant.
  Risk indicators announce their text label and concern level.
- **Dark mode:** Text, icons, surfaces, borders, and status indicators remain legible in both
  light and dark appearance.
- **RTL readiness:** Layout direction, alignment, navigation affordances, and reading order work
  in a right-to-left locale. Do not mirror icons whose meaning is direction-independent.

Product-wide checks also apply wherever relevant: use "risk indicator" or "concern level" wording,
never claim that a product or ingredient is safe/unsafe, and preserve a distinct unknown state.

## Current route audit

These are scaffold observations only, not final screen sign-offs.

| Route         | Current owner/task          | Current state                                                                    | Audit status                                                                                                         |
| ------------- | --------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `/`           | Dev 3 - MOB-06 (Home)       | Placeholder heading with `header` accessibility role; no controls                | Pending replacement by the Home screen, then run all sign-off checks.                                                |
| Unknown route | Dev 3 - MOB-10 (resilience) | Placeholder heading with `header` role and home link styled with `minHeight: 44` | Pending shared error/empty state and i18n; verify the rendered link target and screen-reader announcement on device. |

The root stack currently has no visible controls. Product detail (MOB-05) is implemented at
`/products/[productId]`; run the checks below on device before signing it off. Scan (MOB-04), product
list (MOB-07), search (MOB-08), filters (MOB-09), and methodology/disclaimer (MOB-11) are not
present in this scaffold, so they have no audit result yet. MOB-02 is an API foundation and has no
user-facing screen to audit. Run this checklist after each remaining screen lands, including the
work in progress from the other developers.

## Per-screen sign-off template

Copy this section for each implemented screen. Record the device/simulator, OS version, locale,
appearance, and text-size setting used. Link any defects to the issue or pull request that fixes
them.

### Screen: <name> (`<route>`)

- Owner/task:
- Implementation revision:
- Device/simulator and OS:
- Locale and layout direction:
- Appearance and text-size setting:
- Grayscale: Pending
- Large text: Pending
- Touch targets: Pending
- Screen reader: Pending
- Dark mode: Pending
- RTL readiness: Pending
- Defects/follow-up:
- Reviewer and date:
- Sign-off: Pending
