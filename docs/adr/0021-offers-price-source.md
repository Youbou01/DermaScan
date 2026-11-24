# ADR-0021: Offers price source (SerpApi Google Shopping)

- Status: Accepted
- Date: 2026-11-24

## Context

Dev 2 owns US-22 (where to buy online) and US-32 (cheapest offer). Offers are stored in our own
database and filled by a refresh job; the read API never calls a price source.

The catalog is global: some products are not sold in Tunisia, so one global source is needed,
chosen per run by `PRICE_SOURCE`. Options considered:

- **Scraping pharma-shop.tn** (existing ingestion code): postponed. Article 8 of its terms says
  the content belongs to the shop and only personal, private copying is allowed ("any other use
  strictly forbidden"). It needs written permission from the shop or written approval of the
  project leader. The existing ingestion site files also use `respect_robots: false` at 25 rps,
  a risk the leader should know about.
- **eBay Browse API**: its `gtin` filter accepts only UPC, so it cannot match our EAN-13 barcodes.
- **SerpApi Google Shopping**: chosen. Free plan: 250 searches per month; paid Starter plan:
  25 USD per month for 1,000 (vendor pricing page, not re-checked since). Tunisia is not a
  supported country, so searches use `gl=fr`, `hl=fr` and prices are in EUR.

## Decision

1. `PRICE_SOURCE` selects one source per run: `fixture` (default) or `serpapi`. No fallback from
   one to the other. When SerpApi fails, the failure is logged, existing offers are kept (they
   become stale) and the worker never crashes. Without `SERPAPI_API_KEY` nothing is stored.
2. **The fixture is DEMO data** (deterministic fake prices) and exists for tests, CI, demos and
   key-less development. It is the default of `PRICE_SOURCE`: real prices need
   `PRICE_SOURCE=serpapi` and `SERPAPI_API_KEY` in the backend `.env` only.
3. **Two searches per product**: a Google Shopping search by text, then the "immersive product"
   request (`more_stores=true`) of the chosen result, which lists the shops with direct links.
   The free plan therefore covers roughly 125 products per month (whether the second request is
   counted was not verified).
4. **Barcodes do not work.** Google Shopping has no GTIN lookup: in real calls a barcode query
   returned unrelated products (a toy motorbike, a helmet, a video game), and the barcode
   appeared in responses only as an echo of the query. The adapter searches by "brand + name".
5. **Matching is approximate and strict on purpose.** A result is used only if its title contains
   every distinctive word of the query, and no gift/pack/kit style word that the query lacks. A
   name that looks like a category path (contains `/`) or has fewer than 3 distinctive words is
   not searched. Among matching results, one sold by several shops is preferred. Offers priced
   below half or above double the median are dropped. **An empty offer list is better than the
   offers of another product.**
6. **Stock** is read from the offer details: "En stock" gives `in_stock`, anything else gives
   `unknown`. An `unknown` offer is never the cheapest. Prices are item prices, shipping excluded.
7. `logo_url` is null (the app shows initials). Product name and brand come from
   `CatalogService.get_product_detail`; a lighter `exists` call is a follow-up for the catalog owner.

## Consequences

- **Results are not stable.** The same query returned very different result lists in consecutive
  real calls (with caching disabled, none of the results were the product asked for). Cached
  results can hide this for an hour. Expect empty offer lists for many products.
- Generic names without a brand ("Daily Moisture") get no offers. A matching row can still be a
  similar product (for example another size or texture of the same brand).
- Real-call evidence is small: a handful of products, mostly from one session. It is not a
  measured success rate.
- The SerpApi key must never be committed or logged; the adapter never puts it in error messages.
- If the leader wants dependable prices, the next step is a source with GTIN lookup, or written
  permission to scrape a Tunisian shop.
