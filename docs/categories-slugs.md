# Category slugs (API contract)

Stable, lowercase, kebab-case ASCII slugs. They are **never translated** and must not
change once published: the mobile app (icons, i18next keys) and the ingestion category
mapper (task E3) depend on them.

Display names live in `category_translation` and are returned by the API according to
`Accept-Language`. Prefer the `slug` for app logic; use `name` only for labels.

## Tree

| Slug | Parent | English | French |
|---|---|---|---|
| `face-care` | — | Face care | Soin du visage |
| `cleanser` | face-care | Cleanser | Nettoyant |
| `toner` | face-care | Toner | Tonique |
| `serum` | face-care | Serum | Sérum |
| `moisturizer` | face-care | Moisturizer | Hydratant |
| `face-mask` | face-care | Face mask | Masque |
| `exfoliant` | face-care | Exfoliant | Exfoliant |
| `eye-care` | face-care | Eye care | Contour des yeux |
| `sun-care` | — | Sun care | Protection solaire |
| `sunscreen` | sun-care | Sunscreen | Écran solaire |
| `after-sun` | sun-care | After-sun | Après-soleil |
| `body-care` | — | Body care | Soin du corps |
| `body-lotion` | body-care | Body lotion | Lait corps |
| `body-wash` | body-care | Body wash | Gel douche |
| `lip-care` | — | Lip care | Soin des lèvres |

Endpoint: `GET /api/v1/categories` (tree of top-level nodes with `children`).

## Adding a category safely

1. Add the node (and English + French names) to
   `backend/src/app/modules/ingestion/data/categories.json`.
2. Pick a **new** slug; do not rename an existing one (add a new slug and deprecate the old
   one in a later migration/release if needed).
3. Run `uv run python scripts/seed_categories.py` (idempotent: updates names, no duplicates).
4. Tell the mobile team about the new slug before relying on it in production.
