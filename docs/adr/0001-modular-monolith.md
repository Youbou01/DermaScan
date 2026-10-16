# ADR-0001: Modular monolith with service-oriented boundaries
- Status: Accepted
- Date: 2026-10-16

## Context
The project asks for a service-oriented architecture (SOA). Four developers are building a first
version; separately deployed services would add network contracts, distributed transactions,
several pipelines and harder debugging, with no benefit at this scale.

## Decision
One deployable FastAPI application, split into modules (`ingredients`, `scoring`, `catalog`,
`ingestion`) that behave like services: each owns its tables and exposes a public interface
(its `__init__.py`: service functions and DTOs). One PostgreSQL database, one schema.
Rules are enforced by `import-linter` in pre-commit and CI, not by discipline:
dependencies only point downward (`ingestion → catalog → ingredients | scoring → core`),
and only a module itself may import its `models` / `repository`.

## Consequences
- Extracting a module into its own service later is a refactor, not a rewrite: its public
  interface already is the contract.
- Cross-module foreign keys are allowed in the database, but there is no `relationship()`
  across modules and no cross-module joins; a module asks the other module's service.
- Flows that touch several modules (e.g. barcode miss → fetch from Open Beauty Facts → save)
  live in a thin orchestration layer at the top, never inside a lower module.
- Strictness costs a little at first (the linter says no); it prevents spaghetti later.
