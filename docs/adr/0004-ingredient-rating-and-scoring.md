# ADR-0004: Ingredient ratings and product scoring
- Status: Accepted (weights and thresholds pending, see task C2)
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

## Open
Penalty weights, band thresholds and the coverage threshold are decided in a team session
(task C2) and recorded by amending this ADR.
