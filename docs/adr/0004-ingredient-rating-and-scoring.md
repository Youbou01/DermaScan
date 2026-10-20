# ADR-0004: Ingredient ratings and product scoring
- Status: Accepted (numbers decided 2026-10-19, see Amendment 1)
- Date: 2026-10-16

## Context
Users want a quick judgement of a product and of each ingredient. We publish these ratings, so
we are responsible for them being defensible and for not overstating certainty.

## Decision
- **Ingredients carry an ordinal level** (`low / moderate / high / unknown`), never a fine-grained
  number nobody can defend ("63 vs 58"). `unknown` is never treated as safe.
- **Moderate/high ratings must cite a source** (`source_ref`, enforced by the database) and have an
  English rationale (enforced by the seed-file validator); French is optional.
- **The product score is computed, not averaged**: start from 100, subtract penalties weighted by risk
  level and by label position, and apply a cap so one high-concern ingredient limits the band
  whatever else the product contains. Averaging would hide exactly that case.
- **Coverage**: `score_coverage` is the share of ingredients we recognized. Below a threshold the
  product shows "insufficient data" instead of a score.
- **Scores are precomputed and stored** with `scoring_version`. The algorithm is a pure function
  (easy to test exhaustively). Changing it bumps the version; stale rows are found with
  `scoring_version < current` and recomputed by a CLI job.
- **Wording**: "risk indicator" / "concern level" based on a named methodology, never "safe/unsafe",
  plus a disclaimer. The API returns semantic levels; the app maps them to colour + icon + label
  (colour is never the only signal).
- **Sponsored content must never influence a score or a rating.**

## Amendment 1: the numbers (task C2), 2026-10-19
Decided and recorded here, as this ADR said they would be. The code is the single source:
`app/modules/scoring/engine.py`. A change to any value below is a new amendment **and** a
`SCORING_VERSION` bump.

| Parameter | Value |
|---|---|
| Base points, low / moderate / high | 100 / 55 / 10 |
| Position weight | `1 / (1 + 0.2 * (position - 1))` |
| Any high-concern ingredient | score capped at **49** (the band can never be "good") |
| Bands | good >= 75, moderate >= 40, otherwise poor |
| Minimum coverage to publish a score | **0.70**: below it the result is "insufficient data" (no score) |
| Coverage needed for "good" | **0.80**: below it the score is capped at **74** |
| `SCORING_VERSION` | **2** |

**Why the two coverage rules.** Unknown ingredients are left out of the weighted average, so a
product with half of its ingredients unknown could score 100 and be "good": exactly the "unknown
looks safe" case this ADR forbids. The 0.70 minimum stops us from publishing a score on a
mostly-unrecognized label. The 0.80 cap stops a partly-recognized label from reaching "good".
The cap applies to the **score**, not only the band, so the number and the band always agree
(no "90, moderate" on screen).

**Previous values** (version 1): minimum coverage 0.50, no coverage condition for "good".

**Consequences.**
- Every product stored with `scoring_version = 1` is stale. Run
  `uv run python scripts/recompute_scores.py` after deploying.
- Products that were scored on a coverage between 0.50 and 0.70 become "insufficient data".
  Expect the number of scored products to drop until the ingredient dictionary grows (task B6).
- Scripts that insert scored rows by hand must use `SCORING_VERSION`, never a literal.
