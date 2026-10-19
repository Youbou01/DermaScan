# Search and filter API contract (PROPOSED)

Status: **proposed**. The backend developer implements it (tasks D8, D9); the mobile app mocks it
now (MOB-02, MOB-07 to MOB-09) and switches to the real endpoints without changing its code.
Once implemented and merged, remove "proposed" and treat it like `categories-slugs.md`: changing
a field or parameter is a breaking change, mention it in the PR.

Conventions that apply to both endpoints (see ADR-0007): everything under `/api/v1`, errors are
`application/problem+json` and the app switches on `type`, pagination is keyset-based with an
opaque `cursor`, display text follows `Accept-Language`.

## `GET /api/v1/products`: list, search and filter

| Parameter | Type | Meaning |
|---|---|---|
| `q` | string, 2 to 100 chars, optional | Name search: accent-insensitive, fuzzy + prefix ("creme" finds "Crème"). |
| `category` | category slug, optional | Includes the category's children (`face-care` returns serums, cleansers, ...). Unknown slug: 422 `invalid-category`. |
| `band` | repeatable `low` / `moderate` / `high`, optional | Product risk band. `unknown` (insufficient data) is **not** accepted here. |
| `min_score`, `max_score` | integer 0 to 100, optional | Inclusive. `min_score > max_score`: 422 `invalid-score-range`. |
| `include_ingredient` | repeatable ingredient id (uuid), optional | Product contains **all** of them. |
| `exclude_ingredient` | repeatable ingredient id (uuid), optional | Product contains **none** of them. |
| `cursor` | opaque string, optional | From the previous page's `next_cursor`. Malformed: 400 `invalid-cursor`. |
| `limit` | integer 1 to 50, default 10 | Same bounds as the home feed. Out of range: 400 `invalid-limit`. |

Response `200`:

```json
{ "items": [ProductCard], "next_cursor": "opaque-or-null" }
```

`ProductCard` is the existing `ProductCardOut` (`id`, `name`, `brand`, `image_url`, `score`,
`score_band`, `category_slug`). No new shape.

**Ordering** (needed so the cursor is stable; decide and document in the endpoint):
- with `q`: relevance first, then score, then id;
- without `q`: score descending (unscored products last), then id.

A cursor is only valid for the exact same filters; if they differ the server answers 400 `invalid-cursor`.

### Behaviour the mobile app relies on
- **No filters at all** is valid (it is the category-less "everything" list).
- Filters combine with AND.
- Products with no score (insufficient data) are returned when no score/band filter is set
  (the app shows them as "not enough data", never as good) and are excluded as soon as
  `band`, `min_score` or `max_score` is set.
- An empty result is `200` with `items: []` and `next_cursor: null`, never 404.
- The mobile "risk band" labels map 1:1 to `band` values (`low` = low concern).

## `GET /api/v1/ingredients/search`: autocomplete for the include/exclude chips

| Parameter | Type | Meaning |
|---|---|---|
| `q` | string, 2 to 100 chars, required | Matched through the same normalization as alias matching (accent- and case-insensitive; also finds common aliases, e.g. "aqua" finds "Water"). |
| `limit` | integer 1 to 20, default 8 | |

Response `200`: `[ { "id": "<uuid>", "inci_name": "Glycerin" } ]`, best match first.

## Decisions to confirm (these differ from the first draft)

1. **Repeated parameters, not comma-separated lists.** The first draft had `band=low,moderate`.
   Use `band=low&band=moderate` (FastAPI `list[RiskLevel] = Query(None)`). It documents and types
   cleanly in OpenAPI, so the generated TypeScript client gets a real `("low" | "moderate" | "high")[]`
   instead of a string we would have to split and validate by hand. Same for the ingredient parameters.
2. **`unknown` is not a filterable band.** "Insufficient data" is a state, not a risk level to shop by.
3. **`GET /ingredients/search` returns a bare list.** Consistent with `GET /categories`. If we ever
   need paging or metadata it becomes a breaking change, so say now if you want an
   `{ "items": [...] }` envelope instead.
