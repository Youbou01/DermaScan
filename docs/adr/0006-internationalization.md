# ADR-0006: Internationalization
- Status: Accepted
- Date: 2026-10-16

## Context
French and English at launch; Arabic (right-to-left) very likely later.

## Decision
- The API returns **codes and enums** (category slug, risk level, error `type`); the mobile app
  translates them with i18next (`categories.moisturizer` → "Hydratant").
- Free text users read from the database lives in **translation tables** keyed by `(id, locale)`:
  `category_translation(name)` and `ingredient_translation(rationale)`. Locale is a two-letter
  lowercase code enforced by a CHECK constraint. English is required and is the fallback.
- Ingredients are displayed by their **INCI name** (that is what is printed on every label).
- The API picks the locale from the `Accept-Language` header, falling back to `en`.
- Search normalization (lowercase, unaccent, trigram) is language-agnostic, so Arabic works later.

## Consequences
Adding Arabic means new translation rows, RTL layout work in the app, and Arabic alias entries; no schema change.
