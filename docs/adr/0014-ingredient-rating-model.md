# ADR-0014: Ingredient Rating Model and Consensus Architecture

- Status: Accepted
- Date: 2026-10-20

## Context

Previous iterations relied on a coarse 3-tier risk classification (`low`, `moderate`, `high`) derived from a small seed list (~24 ingredients), causing thousands of ingredients to remain unrated or fall into "unknown" bands. Moreover, single-model AI ratings are vulnerable to hallucinations and numerical drift, while manual cosmetic expert sign-off creates a human bottleneck incompatible with autonomous scaling.

## Decision

Implement an objective, continuous rating engine operating on a $0.0$ to $10.0$ scale ($10.0 =$ least concern, $0.0 =$ highest concern) with regulatory overrides and dual-model consensus:

1. **Continuous Rating Scale:**
   - `9.0 to 10.0`: Water, glycerin, physiologically native, well-established benign substances.
   - `7.0 to 8.9`: Low concern, generally well-tolerated cosmetic ingredients.
   - `4.0 to 6.9`: Moderate concern, known irritants, sensitizers, or penetration enhancers.
   - `0.0 to 3.9`: High concern, prohibited substances, strong sensitizers, or endocrine disruptors.

2. **EU CosIng Regulatory Override (Absolute Precedence):**
   - **Prohibited Substances (Annex II):** Rating is deterministically forced to `0.5`, `rating_source = regulatory`, bypassing LLM rating calls.
   - **Restricted Substances (Annex III) & Fragrance Allergens:** Rating is capped at `8.0` (never classified as perfectly benign).

3. **Two-Model Consensus Formula:**
   - Primary model ($r_1, c_1$) and independent second-opinion model ($r_2, c_2$) from different provider families (e.g. Gemini + Groq/Ollama):
     - $|r_1 - r_2| \le 1.5$: $r = \frac{r_1 + r_2}{2}, c = \min(c_1, c_2)$, `review_status = auto`.
     - $1.5 < |r_1 - r_2| \le 3.0$: $r = \frac{r_1 + r_2}{2}, c = \min(c_1, c_2) \times 0.6$, `review_status = needs_review`.
     - $|r_1 - r_2| > 3.0$: $r = \min(r_1, r_2)$ (conservative), $c = 0.3$, `review_status = needs_review`.
     - Single model fallback: $r = r_1, c = c_1 \times 0.7$.

4. **Curated Protection Rule:**
   - Any ingredient rated with `rating_source = curated` is immutable to AI overwrite. AI jobs skip curated entries.

5. **Plain-Language Text Validation:**
   - Never use alarmist or medicalized words: *safe, unsafe, toxic, harmful, dangerous*.
   - Word count limits: Summary $\le 20$ words, concern note $\le 30$ words.
   - Bilingual generation (English and French).

6. **Alias Adjudication:**
   - Unmatched frequent label tokens are retrieved with `pg_trgm` candidates and adjudicated via LLM (`source = ai`, threshold $\ge 0.8$).

## Consequences

- Objective, reproducible ratings without subjective human bottlenecks.
- Absolute compliance with EU cosmetic safety regulations.
- Deterministic invalidation: changing an ingredient rating automatically marks all dependent products `score_dirty = True`.
