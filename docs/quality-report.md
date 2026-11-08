# DermaScan Quality and Health Report

*Generated on: 2026-11-08 16:52:25 UTC*

## 1. Catalog Coverage Overview

- **Total Products**: 15,912
- **With Category**: 2,273 (14.3%)
- **With Brand**: 14,743 (92.7%)
- **With Image**: 3 (0.0%)
- **With >= 5 Parsed Ingredients**: 15,226 (95.7%)

## 2. Risk Band & Scoring Quality (Phase 0 Targets)

- **Stale / Dirty Scores Remaining**: 0 (target: 0)
- **Ingredient Items > 120 Characters**: 0
- **Unknown Band Share (Products >= 5 Ingredients)**: 0.0% (0/15,226)

### Score Bands Distribution

| Risk Level | Count | Share |
|---|---|---|
| `low` | 606 | 3.8% |
| `moderate` | 4,495 | 28.2% |
| `high` | 10,811 | 67.9% |
| `unknown` | 0 | 0.0% |

### Numerical Score Buckets (0-100)

| Range | Count | Share (of total) |
|---|---|---|
| 80 - 100 (Safe/Clean) | 109 | 0.7% |
| 60 - 79 | 4,451 | 28.0% |
| 40 - 59 | 582 | 3.7% |
| 20 - 39 | 10,725 | 67.4% |
| 0 - 19 (High concern) | 45 | 0.3% |
| Unscored (`None`) | 0 | 0.0% |

## 3. Ingestion & Pipeline Staging (Phase 1 & 2)

- **Raw Products Total**: 19
- **Ingestion Runs Total**: 5
- **Quarantine Items Total**: 748

### Raw Products By Source

| Source | Count |
|---|---|
| `open_beauty_facts` | 11 |
| `scrape` | 7 |
| `user_photo` | 1 |

### Quarantine Items By Status

| Status | Count |
|---|---|
| `approved` | 2 |
| `pending` | 744 |
| `rejected` | 2 |

### Quarantine Items By Reason

| Reason | Count |
|---|---|
| `ambiguous_duplicate` | 5 |
| `insufficient_valid_ingredients` | 734 |
| `not_skincare` | 1 |
| `parser_llm_disagree` | 8 |

## 4. Product Enrichment & Media Pipeline

### Enrichment Status

| Status | Count |
|---|---|
| `done` | 6 |
| `pending` | 15,906 |

### Product Image Status

| Image Status | Count |
|---|---|
| `none` | 15,909 |
| `processed` | 3 |

## 5. Ingredient Intelligence & Ratings

- **Total Ingredients in Dictionary**: 24,008

### Ratings By Source

| Rating Source | Count |
|---|---|
| `ai` | 2,747 |
| `curated` | 173 |
| `regulatory` | 872 |
| `unrated` | 20,216 |

## 6. PostgreSQL Job Queue Status

- **Total Jobs Tracked**: 2,386

| Job Status | Count |
|---|---|
| `completed` | 2,377 |
| `failed` | 6 |
| `pending` | 3 |

## 7. Overhaul Verification Summary

- **Scoring v3 Algorithm**: Active across 100% of products (`scoring_version = 3`).
- **PostgreSQL Job Queue**: Active (`app/core/jobs.py` + `app/worker.py`).
- **Enrichment Gateway**: Multi-provider fallback and rate limiting active.
- **Product Provenance**: Source precedence (`curated > retailer/brand > obf > ai`).
- **Multilingual Localization**: Strict INCI preservation, Arabic support.
- **Self-Hosted Image Pipeline**: 1024x1024 + 320x320 WebP, no hotlinking.
