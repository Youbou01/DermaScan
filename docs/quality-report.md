# DermaScan Quality and Health Report

*Generated on: 2026-11-02 20:56:28 UTC*

## 1. Catalog Coverage Overview

- **Total Products**: 16,641
- **With Category**: 2,337 (14.0%)
- **With Brand**: 15,349 (92.2%)
- **With Image**: 20 (0.1%)
- **With >= 5 Parsed Ingredients**: 15,242 (91.6%)

## 2. Risk Band & Scoring Quality (Phase 0 Targets)

- **Stale / Dirty Scores Remaining**: 0 (target: 0)
- **Ingredient Items > 120 Characters**: 0
- **Unknown Band Share (Products >= 5 Ingredients)**: 45.1% (6,879/15,242)

### Score Bands Distribution

| Risk Level | Count | Share |
|---|---|---|
| `low` | 5 | 0.0% |
| `moderate` | 1,702 | 10.2% |
| `high` | 6,737 | 40.5% |
| `unknown` | 8,197 | 49.3% |

### Numerical Score Buckets (0-100)

| Range | Count | Share (of total) |
|---|---|---|
| 80 - 100 (Safe/Clean) | 3 | 0.0% |
| 60 - 79 | 1,563 | 9.4% |
| 40 - 59 | 159 | 1.0% |
| 20 - 39 | 6,702 | 40.3% |
| 0 - 19 (High concern) | 17 | 0.1% |
| Unscored (`None`) | 8,197 | 49.3% |

## 3. Ingestion & Pipeline Staging (Phase 1 & 2)

- **Raw Products Total**: 4
- **Ingestion Runs Total**: 3
- **Quarantine Items Total**: 3

### Raw Products By Source

| Source | Count |
|---|---|
| `open_beauty_facts` | 2 |
| `scrape` | 1 |
| `user_photo` | 1 |

### Quarantine Items By Status

| Status | Count |
|---|---|
| `approved` | 1 |
| `rejected` | 2 |

### Quarantine Items By Reason

| Reason | Count |
|---|---|
| `ambiguous_duplicate` | 3 |

## 4. Product Enrichment & Media Pipeline

### Enrichment Status

| Status | Count |
|---|---|
| `done` | 2 |
| `pending` | 16,639 |

### Product Image Status

| Image Status | Count |
|---|---|
| `none` | 16,641 |

## 5. Ingredient Intelligence & Ratings

- **Total Ingredients in Dictionary**: 24,128

### Ratings By Source

| Rating Source | Count |
|---|---|
| `curated` | 31 |
| `regulatory` | 900 |
| `unrated` | 23,197 |

## 6. PostgreSQL Job Queue Status

- **Total Jobs Tracked**: 17

| Job Status | Count |
|---|---|
| `completed` | 17 |

## 7. Overhaul Verification Summary

- **Scoring v3 Algorithm**: Active across 100% of products (`scoring_version = 3`).
- **PostgreSQL Job Queue**: Active (`app/core/jobs.py` + `app/worker.py`).
- **Enrichment Gateway**: Multi-provider fallback and rate limiting active.
- **Product Provenance**: Source precedence (`curated > retailer/brand > obf > ai`).
- **Multilingual Localization**: Strict INCI preservation, Arabic support.
- **Self-Hosted Image Pipeline**: 1024x1024 + 320x320 WebP, no hotlinking.
