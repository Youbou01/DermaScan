# Mobile accessibility and polish audit

This checklist is the mobile accessibility and quality review record. A screen is signed off only after it has a real UI implementation and each applicable check has been verified on device or in a representative accessibility test.

## Accessibility Principles & Sign-off Checks

For every screen, record **Pass**, **Fail**, or **N/A with a reason** for each applicable item:

- **Grayscale / Color Independence:** Meaning remains clear without color. Risk indicators include an icon and a text label as well as color; `unknown` is presented as insufficient data and never as low-risk.
- **Large text (Dynamic Type):** Increase the device text size to its largest supported setting. Text remains readable, controls remain usable, and content can scroll without clipping or overlap.
- **Touch targets:** Every interactive target is at least 44 by 44 pt, with enough separation to avoid accidental activation.
- **Screen reader (VoiceOver / TalkBack):** Controls have useful accessible names and roles; reading order follows the visual order; dynamic loading, empty, error, and success states are announced when relevant.
- **Dark mode:** Text, icons, surfaces, borders, and status indicators remain legible in both light and dark appearance.
- **Tone & Product Guidelines:** Always use "risk indicator" or "concern level" wording. Never claim that a product or ingredient is absolute "safe" or "unsafe", and preserve a distinct unknown/insufficient data state.

## Implemented Routes Audit Checklist

| Route                      | Functionality                                | Accessibility Status    | Notes                                                         |
| :------------------------- | :------------------------------------------- | :---------------------- | :------------------------------------------------------------ |
| `/(tabs)/index`            | Home shelves, search, categories             | Complete                | Touch targets $\ge 44$pt, HeroUI accessible primitives        |
| `/categories`              | Category tree                                | Complete                | Accessible list navigation                                    |
| `/product/[id]`            | Product detail & score breakdown             | Complete                | High-contrast badges, ingredient disclosure                   |
| `/scan`                    | Camera barcode scanner & manual entry        | Complete                | VoiceOver labels on torch/input, web fallback                 |
| `/analysis`                | Ingredient label OCR analysis                | Complete                | Clear text alternatives for photo capture                     |
| `/routines`                | Routine CRUD & daily habit completion        | Complete                | Haptic feedback and clear action button labels                |
| `/routine/add`             | Routine step builder                         | Complete                | Step type selectors and reordering affordances                |
| `/recommendations`         | Conflict-free routine suggestions            | Complete                | Skin-type segmented control                                   |
| `/account`                 | Sign-in & registration                       | Complete                | Secure input fields, clear error announcements                |
| `/profile`                 | Skin profile, health conditions & allergies  | Complete                | Multi-select condition tags                                   |
| `/avoidance`               | Avoided / blacklisted products & ingredients | Complete                | Clear deletion and addition affordances                       |
| `/contribute`              | Photo contribution upload                    | Complete                | High-contrast form controls and photo picker                  |
| `/library/saved`           | Saved product list and remove action         | Pending device sign-off | Account-private list, accessible product/action labels        |
| `/library/recently-viewed` | Recently viewed product history              | Pending device sign-off | Account-private list, accessible product navigation           |
| `/dermatologists`          | Curated dermatologist guidance               | Pending device sign-off | Source links, credential text, and informational notice       |
| `/shared-routine/[token]`  | Public routine view and confirmed copy       | Pending device sign-off | Public view works logged out; copy requires slot confirmation |

## Per-screen sign-off template

Copy this section for device-level sign-off:

### Screen: <name> (`<route>`)

- Device/simulator and OS:
- Locale and layout direction:
- Appearance (Light / Dark):
- Text-size setting (Dynamic Type):
- Grayscale check: Pass / Fail
- Large text check: Pass / Fail
- Touch targets ($\ge 44\times 44$ pt): Pass / Fail
- Screen reader (VoiceOver / TalkBack): Pass / Fail
- Reviewer and date:
