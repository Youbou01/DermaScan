# ADR-0005: Data sources, scraping policy and licensing
- Status: **Proposed**: needs an owner to complete the checklist below
- Date: 2026-10-16

## Context
We need products (with barcodes and ingredient lists) and ingredient risk data. Open Beauty Facts
(OBF) is free, but its terms must be understood before we build on it. Tunisian products are likely
under-represented (their barcodes start with 619).

## Proposed decision
1. **Products**: import OBF in batch from its data dump (not one API call per product); on a barcode
   miss, query OBF's live API once and import the product; otherwise return a clean 404 and record the
   barcode in a "demand list".
2. **Ingredient ratings**: a curated file in the repo, seeded from defensible public sources (EU Cosmetics
   Regulation annexes via CosIng, SCCS opinions), reviewed through pull requests. Do not copy
   proprietary rating databases (e.g. EWG): legal risk and not defensible.
3. **Scraping**: never live, never triggered by a user request. Only offline, admin-triggered batches,
   into a staging area, normalized and reviewed before reaching real data, and only on sites whose
   terms allow it. Preferred ways to get Tunisian products: user submissions (barcode + photo of the
   ingredient list, reviewed) and local pharmacy/brand partnerships.

## Checklist before accepting (owner: ____)
- [ ] Read the OBF licence terms (database licence, contents licence, image licence) and write down
      what we must do: attribution wording, and what applies to our derived data
- [ ] Decide where attribution appears in the app and the API
- [ ] Measure coverage (task E1): products with ingredients, mappable categories, 619-prefixed barcodes
- [ ] Get a short legal opinion before public launch (Tunisian and EU rules differ)

## Consequences
`product.source` + `source_id` are stored so imports are idempotent and attribution is traceable.
