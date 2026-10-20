# Architecture Decision Records

Short notes explaining *why* we chose something, so nobody has to guess later.
One file per decision, numbered, never rewritten: to change a decision, add a new ADR that
supersedes the old one (and mark the old one `Superseded by ADR-00XX`). The only exception is a
decision that explicitly left something open (like the scoring numbers in ADR-0004): fill it in
with a dated, numbered `Amendment` section instead of editing the original text.

Write one when a choice is hard to reverse, surprising to a newcomer, or took a real discussion.

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with service-oriented boundaries | Accepted |
| [0002](0002-postgresql-only.md) | PostgreSQL for data and search; no extra infrastructure yet | Accepted |
| [0003](0003-schema-conventions.md) | Schema conventions: UUIDv7, enums, constraints, naming | Accepted |
| [0004](0004-ingredient-rating-and-scoring.md) | Ingredient ratings and product scoring approach | Accepted (numbers decided, Amendment 1) |
| [0005](0005-data-sources-and-licensing.md) | Data sources, scraping policy and licensing | **Proposed** (needs owner) |
| [0006](0006-internationalization.md) | Internationalization: codes in the API, translations in tables | Accepted |
| [0007](0007-api-conventions.md) | API conventions: errors, request IDs, pagination, contract | Accepted |
| [0008](0008-engineering-quality-gates.md) | Tooling and quality gates | Accepted |
| [0009](0009-ingredient-matching.md) | Ingredient matching is exact; fuzzy only suggests | Accepted |
| [0010](0010-mobile-stack.md) | Mobile stack: Expo SDK 58, Router, generated API client | Accepted |

## Template
```markdown
# ADR-00XX: Title
- Status: Proposed | Accepted | Superseded by ADR-00YY
- Date: YYYY-MM-DD

## Context
What problem, what constraints, what options existed.

## Decision
What we chose, in one or two sentences.

## Consequences
What gets easier, what gets harder, what we must watch.
```
