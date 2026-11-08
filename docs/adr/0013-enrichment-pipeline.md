# ADR-0013: AI Enrichment Pipeline and Raw Store Architecture

- Status: Accepted
- Date: 2026-10-20

## Context

DermaScan ingests product data from multiple diverse sources:
1. Open Beauty Facts bulk dumps and live barcode lookups.
2. Direct brand and public retailer product web pages.
3. User packaging photo contributions (future).

Directly mapping messy external data into the canonical catalog risks data corruption, silent loss of original source data, and difficulty in re-evaluating or auditing normalization logic when rules improve.

## Decision

Adopt an immutable raw store and an asynchronous AI-in-the-middle enrichment pipeline:

1. **Immutable Raw Store (`raw_product`):**
   - Every external record is stored verbatim in `raw_product` (`source`, `source_id`, `payload jsonb`, `content_hash char(64)`, `fetched_at`).
   - Idempotency is enforced at the database level by unique constraint `(source, source_id, content_hash)`.
   - Raw records are never mutated or deleted.
2. **Pluggable Source Adapters (`SourceAdapter` Protocol):**
   - All ingestion mechanisms (OBF bulk dumps, OBF live API, web scrapers) implement `SourceAdapter`:
     - `discover(**kwargs) -> AsyncIterator[dict]`
     - `fetch(source_id) -> dict | None`
     - `to_raw(payload, url) -> RawRecord`
3. **Four-Stage AI Middleware Pipeline:**
   - **Stage 1 (Deterministic Mapper):** Fast field filtering, category exact match, barcode GTIN validation.
   - **Stage 2 (LLM Enrichment):** Model extraction of standardized product name, bilingual translations, clean label INCI ordering, and claim removal.
   - **Stage 3 (Deterministic Validation):** Token Jaccard check against label parser output, length constraints ($\le 120$ characters), skincare confirmation.
   - **Stage 4 (Publish with Provenance):** Upsert to catalog with strict precedence (`curated > retailer > OBF > AI-guess`). Lower precedence never overwrites higher precedence.
4. **Quarantine:**
   - Records failing validation or exhibiting strong parser-LLM disagreement are routed to `quarantine_item` with explicit reason codes for administrative review.

## Consequences

- Auditable lineage: Every catalog product can be traced directly back to its original raw external payload.
- Resilient ingestion: Ingestion runs do not fail on individual malformed products.
- Low quota consumption: Bulk ingestion stores raw data first, enabling batched, throttled enrichment jobs without dropping records.
