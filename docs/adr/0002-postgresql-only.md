# ADR-0002: PostgreSQL for data and search; no extra infrastructure yet
- Status: Accepted
- Date: 2026-10-16

## Context
Sprint 1 needs name search, category and score filters, and ingredient include/exclude
filters over a catalogue that starts in the thousands to low hundreds of thousands of products.

## Decision
Use PostgreSQL only: full-text search, `pg_trgm` (typo tolerance) and `unaccent`
(accent-insensitive French/English matching). No Elasticsearch, Redis, task queue or
API gateway until a measurement shows a concrete need.
Accent-insensitive indexes use a stored normalized column (the same normalizer as ingredient
aliases) because `unaccent()` cannot be used directly in an index expression.

## Consequences
- One system to run, back up and understand.
- Revisit when search latency or relevance is measurably insufficient, or when background
  work (imports, recomputation) must run continuously rather than as CLI jobs.
- Rate limiting for the public API is still required; decide at the infrastructure level
  before launch.
