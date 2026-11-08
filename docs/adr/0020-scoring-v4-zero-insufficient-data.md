# ADR-0020: Scoring Algorithm v4 (Zero Insufficient Data & Regulatory Heuristics)

- Status: Accepted (supersedes the `score = NULL / band = unknown` insufficient-data rule of ADR-0015)
- Date: 2026-11-03

## Context

Under ADR-0015 (Scoring v3), products where exposure-weighted confidence $K < 0.35$ or ingredient count $< 3$ returned `score = NULL` and `score_band = unknown`. In production:
1. Consumer mobile UX suffered severely when newly scanned or partially parsed products showed "Insufficient Data" rather than actionable guidance.
2. Many safe, unrated cosmetic ingredients (e.g. emollients, solvents, humectants) triggered `score = NULL` despite CosIng function data indicating standard benign use.
3. Products with only 1 or 2 ingredients (e.g., pure argan oil, glycerin solutions) could never receive a score under the $< 3$ ingredient count threshold.

## Decision

Adopt **Scoring v4** (`SCORING_VERSION = 4`):

1. **Zero Insufficient Data Principle:**
   Every product evaluated by `calculate_score` returns a concrete numerical score (`0–100`) and a risk band (`low`, `moderate`, `high`). Neither `score = None` nor `band = RiskLevel.UNKNOWN` is ever returned.

2. **CosIng Regulatory & Functional Heuristics:**
   When an ingredient lacks a curated rating ($r_i = \text{None}$):
   - Prohibited substances (`is_prohibited = True`): effective rating `0.5`, confidence `0.55` (capped at 25 score max, forced `high` band).
   - Restricted substances (`is_restricted = True`): effective rating `4.5`, confidence `0.45`.
   - Allergens (`is_allergen = True`): effective rating `5.0`, confidence `0.45`.
   - Functional heuristics based on CosIng data:
     - Moderate concern functions (preservatives, UV filters/absorbers, hair dyeing, oxidizing, etc.): effective rating `5.5`, confidence `0.40`.
     - Benign functions (humectant, emollient, solvent, skin conditioning/protecting, antioxidant, soothing): effective rating `8.0`, confidence `0.50`.
     - Other functions: effective rating `7.0`, confidence `0.35`.
   - All heuristic paths set confidence $\le 0.50$ so that heuristic-dependent scores are transparently flagged as estimated.

3. **Bayesian Shrinkage Toward Prior ($d_{\text{prior}} = 0.40$):**
   $$d_i^* = c_i \cdot d_i + (1 - c_i) \cdot d_{\text{prior}}$$
   Where $d_i = 1.0 - (r_i / 10.0)$.

4. **Empty Product Fallback:**
   If a product has an empty ingredient list, default to `score = 50`, `band = moderate`, `confidence = 0.10`, `is_estimated = True`.

5. **Transparency via `is_estimated`:**
   A score is flagged with `score_is_estimated = True` whenever:
   - Exposure-weighted confidence $K < 0.60$, OR
   - Total parsed ingredient count $< 3$.

6. **Position Weights & Aggregation:**
   - Position weight $w_i = \max(0.05, 0.85^{i-1})$.
   - Power mean aggregation with $q = 3.0$:
     $$C = \left( \frac{\sum_i w_i \cdot (d_i^*)^q}{\sum_i w_i} \right)^{1/q}$$
   - Final score: $\text{round}(100 \cdot (1 - C))$, clamped to $[0, 100]$.
   - Risk bands:
     - Score $\ge 75$: `low`
     - Score $50 \text{ to } 74$: `moderate`
     - Score $< 50$ or prohibited: `high`
