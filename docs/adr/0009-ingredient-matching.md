# ADR-0009: Ingredient matching is exact; fuzzy matching only suggests
- Status: Accepted
- Date: 2026-10-18

## Context
A label item ("Glycérine", "Aqua (Water)") must be tied to one dictionary ingredient so its risk
rating can be used. We tested typo-tolerant (trigram) matching on PostgreSQL:

| pair | similarity | same ingredient? |
|---|---|---|
| sodium laureth sulfate / sodium lauryl sulfate | 0.72 | NO (different chemicals, different risk) |
| glycerin / glycerine | 0.73 | yes |

No threshold separates the two cases. A wrong match silently gives a wrong rating, which is the
worst failure this product can have.

## Decision
- **Only exact matches on normalized names feed ratings and scores.** `normalize()` (lowercase,
  accents removed, punctuation to spaces) is the single function used both when storing an alias and
  when looking one up.
- **Components:** if the whole item is unknown, its parts are tried ("Aqua (Water)" -> "aqua",
  "water"; "Aqua/Water/Eau"). The item matches (type `component`) only if the known parts all point
  to the SAME ingredient. Parts pointing to different ingredients, or none, mean no match
  ("Retinol (Retinyl Palmitate)" is left for a human).
- **Fuzzy matching is for humans only:** `IngredientService.suggest()` lists look-alike names for the
  review report and the ingredient search box. A suggestion is never applied automatically.
- **Unmatched items are stored, not dropped** (`product_ingredient.ingredient_id IS NULL`), shown as
  `unknown`, and count against `score_coverage`.
- **Aliases are globally unique per normalized key.** Two spellings that normalize identically
  ("Glycerine", "Glycérine") are one alias; the seed loader must deduplicate or reject them.

## Consequences
- Recall depends on the dictionary: curators add the common spellings. The review report (unmatched
  items by frequency, with suggestions) is how the dictionary grows.
- Known limit: "E422" and "E 422", "CI 77891" and "CI77891" are different keys; add both spellings.
  If this proves painful, a "compact key" (spaces removed) is a possible later improvement.
- "(and)" blends such as "Glycol Distearate (and) Laureth-4" stay unmatched until split.
