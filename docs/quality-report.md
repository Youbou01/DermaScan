# DermaScan Quality and Health Report

*Generated on: 2026-11-06 14:21:39 UTC*

## 1. Catalog Coverage Overview

- **Total Products**: 18,032
- **With Category**: 2,412 (13.4%)
- **With Brand**: 16,317 (90.5%)
- **With Image**: 3 (0.0%)
- **With >= 5 Parsed Ingredients**: 17,172 (95.2%)

## 2. Risk Band & Scoring Quality (Phase 0 Targets)

- **Stale / Dirty Scores Remaining**: 0 (target: 0)
- **Ingredient Items > 120 Characters**: 0
- **Unknown Band Share (Products >= 5 Ingredients)**: 0.0% (0/17,172)

### Score Bands Distribution

| Risk Level | Count | Share |
|---|---|---|
| `low` | 859 | 4.8% |
| `moderate` | 5,057 | 28.0% |
| `high` | 12,116 | 67.2% |
| `unknown` | 0 | 0.0% |

### Numerical Score Buckets (0-100)

| Range | Count | Share (of total) |
|---|---|---|
| 80 - 100 (Safe/Clean) | 216 | 1.2% |
| 60 - 79 | 5,131 | 28.5% |
| 40 - 59 | 647 | 3.6% |
| 20 - 39 | 11,960 | 66.3% |
| 0 - 19 (High concern) | 78 | 0.4% |
| Unscored (`None`) | 0 | 0.0% |

## 3. Ingestion & Pipeline Staging (Phase 1 & 2)

- **Raw Products Total**: 14
- **Ingestion Runs Total**: 1
- **Quarantine Items Total**: 1,063

### Raw Products By Source

| Source | Count |
|---|---|
| `open_beauty_facts` | 9 |
| `scrape` | 5 |

### Quarantine Items By Status

| Status | Count |
|---|---|
| `pending` | 1,063 |

### Quarantine Items By Reason

| Reason | Count |
|---|---|
| `ambiguous_duplicate` | 1 |
| `insufficient_valid_ingredients` | 1,054 |
| `parser_llm_disagree` | 8 |

## 4. Product Enrichment & Media Pipeline

### Enrichment Status

| Status | Count |
|---|---|
| `done` | 4 |
| `pending` | 18,028 |

### Product Image Status

| Image Status | Count |
|---|---|
| `none` | 18,029 |
| `processed` | 3 |

## 5. Ingredient Intelligence & Ratings

- **Total Ingredients in Dictionary**: 24,020

### Ratings By Source

| Rating Source | Count |
|---|---|
| `curated` | 391 |
| `regulatory` | 851 |
| `unrated` | 22,778 |

## 6. PostgreSQL Job Queue Status

- **Total Jobs Tracked**: 58

| Job Status | Count |
|---|---|
| `completed` | 57 |
| `failed` | 1 |

## 7. Overhaul Verification Summary

- **Scoring v3 Algorithm**: Active across 100% of products (`scoring_version = 3`).
- **PostgreSQL Job Queue**: Active (`app/core/jobs.py` + `app/worker.py`).
- **Enrichment Gateway**: Multi-provider fallback and rate limiting active.
- **Product Provenance**: Source precedence (`curated > retailer/brand > obf > ai`).
- **Multilingual Localization**: Strict INCI preservation, Arabic support.
- **Self-Hosted Image Pipeline**: 1024x1024 + 320x320 WebP, no hotlinking.
