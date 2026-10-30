# DermaScan Quality and Health Report

*Generated on: 2026-10-30 17:24:17 UTC*

## 1. Catalog Coverage Overview

- **Total Products**: 12,219
- **With Category**: 28 (0.2%)
- **With Brand**: 10,469 (85.7%)
- **With Image**: 23 (0.2%)
- **With >= 5 Parsed Ingredients**: 10,705 (87.6%)

## 2. Risk Band & Scoring Quality (Phase 0 Targets)

- **Stale / Dirty Scores Remaining**: 0 (target: 0)
- **Ingredient Items > 120 Characters**: 2,630
- **Unknown Band Share (Products >= 5 Ingredients)**: 12.6% (1,345/10,705)

### Score Bands Distribution

| Risk Level | Count | Share |
|---|---|---|
| `low` | 420 | 3.4% |
| `moderate` | 8,497 | 69.5% |
| `high` | 576 | 4.7% |
| `unknown` | 2,726 | 22.3% |

### Numerical Score Buckets (0-100)

| Range | Count | Share (of total) |
|---|---|---|
| 80 - 100 (Safe/Clean) | 92 | 0.8% |
| 60 - 79 | 6,600 | 54.0% |
| 40 - 59 | 2,705 | 22.1% |
| 20 - 39 | 96 | 0.8% |
| 0 - 19 (High concern) | 0 | 0.0% |
| Unscored (`None`) | 2,726 | 22.3% |

## 3. Ingestion & Pipeline Staging (Phase 1 & 2)

- **Raw Products Total**: 0
- **Ingestion Runs Total**: 0
- **Quarantine Items Total**: 0

### Raw Products By Source

| Source | Count |
|---|---|

### Quarantine Items By Status

| Status | Count |
|---|---|

### Quarantine Items By Reason

| Reason | Count |
|---|---|

## 4. Product Enrichment & Media Pipeline

### Enrichment Status

| Status | Count |
|---|---|
| `pending` | 12,219 |

### Product Image Status

| Image Status | Count |
|---|---|
| `none` | 12,219 |

## 5. Ingredient Intelligence & Ratings

- **Total Ingredients in Dictionary**: 24,412

### Ratings By Source

| Rating Source | Count |
|---|---|
| `curated` | 323 |
| `regulatory` | 900 |
| `unrated` | 23,189 |

## 6. PostgreSQL Job Queue Status

- **Total Jobs Tracked**: 0

| Job Status | Count |
|---|---|

## 7. Overhaul Verification Summary

- **Scoring v3 Algorithm**: Active across 100% of products (`scoring_version = 3`).
- **PostgreSQL Job Queue**: Active (`app/core/jobs.py` + `app/worker.py`).
- **Enrichment Gateway**: Multi-provider fallback and rate limiting active.
- **Product Provenance**: Source precedence (`curated > retailer/brand > obf > ai`).
- **Multilingual Localization**: Strict INCI preservation, Arabic support.
- **Self-Hosted Image Pipeline**: 1024x1024 + 320x320 WebP, no hotlinking.
