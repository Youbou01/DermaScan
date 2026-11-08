# ADR-0016: Multilingual Product Names and Arabic Support
- Status: Accepted
- Date: 2026-10-30
- Extends: ADR-0006

## Context
ADR-0006 established `category_translation` and `ingredient_translation` tables with English and French at launch, anticipating Arabic later. However, product titles and packaging frequently use mixed languages (English, French, Arabic, German). Open Beauty Facts often provides product names in specific language keys (`product_name_fr`, `product_name_en`, etc.) or in the product's native marketplace language (`source_lang`).

We need:
1. Multilingual product name localization with deterministic fallback order.
2. Formal addition of Arabic (`ar`) as a supported locale across the application.
3. Strict adherence to the INCI standard: chemical and botanical ingredient names are international and language-free; they must never be translated into vernacular terms.

## Decision

1. **Locale Negotiation and Supported Locales (`app/core/i18n.py`):**
   - `SUPPORTED_LOCALES` is updated to `("en", "fr", "ar")`.
   - `resolve_locale(accept_language)` parses quality factors (`q`) and returns `en`, `fr`, or `ar` (defaulting to `en`).
   - Arabic is fully supported as an optional locale; requests with `Accept-Language: ar` gracefully resolve to English or the original product name when Arabic translations are not yet populated.

2. **Product Name Resolution Hierarchy:**
   - Product rows store canonical `name` (the origin label text), `source_lang` (ISO 639-1 code), and `name_i18n` JSONB (`{"en": "...", "fr": "...", "ar": "..."}`).
   - When serving product details, cards, or search summaries:
     `resolve_product_name(product.name, product.name_i18n, locale)`:
     1. `name_i18n[locale]` if non-empty
     2. `name_i18n["en"]` (default locale fallback)
     3. Canonical `product.name` (original un-translated label text)

3. **INCI Non-Translation Rule:**
   - **INCI ingredient names must NEVER be translated.** Ingredients on skincare labels are legally standardized chemical nomenclature (e.g., *Aqua*, *Glycerin*, *Niacinamide*, *Butyrospermum Parkii Butter*).
   - Only human-facing explanations (`ingredient_translation.summary`, `ingredient_translation.concern_note`, and legacy `rationale`) are localized per locale.

4. **Ingredient Aliases:**
   - `ingredient_alias` rows store `language` (e.g., `fr`, `ar`, `de`) to permit localized label text (e.g., French packaging with "Eau", "Beurre de karité") to map deterministically to canonical INCI ingredients.

## Consequences
- The API transparently serves localized product names to Arabic and French clients without breaking existing contracts.
- Missing translations smoothly degrade to English or the physical packaging name.
- Chemical integrity is preserved because INCI nomenclature remains untouched.
