# ADR-0015: Scoring Algorithm v3 (Continuous Power Mean & Shrinkage)

- Status: Accepted (amends ADR-0004)
- Date: 2026-10-20

## Context

The previous scoring formula (v2) relied on heuristic penalties and coarse discrete risk buckets (`low=0, moderate=25, high=100`), leading to:
1. High vulnerability to unrated ingredients ("insufficient data" on products with dozens of benign ingredients).
2. Distortion from single trace ingredients at the end of long ingredient lists.
3. Lack of nuance between mildly concerning ingredients and severe regulatory hazards.

## Decision

Adopt the Scoring v3 mathematical formulation:

1. **Continuous Disutility Metric:**
   For each ingredient $i$ with continuous rating $r_i \in [0.0, 10.0]$:
   $$d_i = \frac{10.0 - r_i}{10.0} \in [0.0, 1.0]$$

2. **Position Weighting ($w_i$):**
   Ingredients appear in descending concentration order on cosmetic packaging. Position weights decrease monotonically down to a floor:
   $$w_i = \max(0.01, 1.0 - 0.04(i - 1))$$

3. **Bayesian Shrinkage Toward Prior ($d_{\text{prior}} = 0.4$):**
   To avoid ignoring unrated or low-confidence ingredients, disutility is shrunk toward a moderately concerning prior:
   $$d_i^* = c_i \cdot d_i + (1 - c_i) \cdot d_{\text{prior}}$$

4. **Power Mean Aggregation ($q = 3$):**
   A power mean ($q=3$) emphasizes the worst ingredients while considering the aggregate formulation:
   $$C = \left( \frac{\sum_{i} w_i \cdot (d_i^*)^q}{\sum_{i} w_i} \right)^{1/q}$$

5. **Final Score Calculation & Caps:**
   $$\text{Score} = \text{round}(100 \cdot (1 - C))$$
   - If any ingredient is prohibited (`is_prohibited = True`): $\text{Score} = \min(\text{Score}, 25)$ and band is forced to `high`.

6. **Confidence & Data Adequacy:**
   - Exposure-weighted coverage: $K = \frac{\sum w_i c_i}{\sum w_i}$ (`score_coverage`).
   - Insufficient data if $K < 0.35$ or total parsed ingredients $< 3$: $\text{Score} = \text{NULL}$, `score_band = unknown`.
   - Estimated (`score_is_estimated = True`) if $K < 0.60$.

7. **Risk Bands:**
   - $\ge 75$: `low`
   - $50 \text{ to } 74$: `moderate`
   - $< 50$: `high`

## Verification Test Vectors

| Case | Score | Coverage (K) | Insufficient | Estimated |
|---|---|---|---|---|
| 20 benign | 95 | 1.000 | False | False |
| 19 benign + 1 high at position 8 | 70 | 1.000 | False | False |
| 1 high at position 1 + 19 benign | 57 | 1.000 | False | False |
| 19 benign + 1 high at position 20 | 84 | 1.000 | False | False |
| 10 unknown | NULL | 0.000 | True | True |
| 6 benign + 4 unknown (last) | 76 | 0.776 | False | False |
| unknown at position 1 + 9 benign | 77 | 0.813 | False | False |
| 5 moderate + 15 benign | 58 | 1.000 | False | False |
| 2 benign only | NULL | 1.000 | True (n < 3) | False |
| 10 benign with confidence 0.5 | 77 | 0.500 | False | True |
