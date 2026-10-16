# ADR-0008: Tooling and quality gates
- Status: Accepted
- Date: 2026-10-16

## Decision
- **uv** for Python versions, dependencies and the lockfile (`uv.lock`); never `pip install`.
- **ruff** (lint + format, including rules that require type hints on every function signature) and
  **mypy --strict**.
- **import-linter** enforces the module boundaries of ADR-0001.
- **pre-commit** runs the checks locally through `uv` (so versions match the lockfile); **GitHub Actions**
  runs the same checks plus migrations (apply, `alembic check`, rollback) and tests on every PR.
- **Tests run on real PostgreSQL** (testcontainers locally, a service container in CI), never SQLite.
  The schema is built by the real migrations; each test is rolled back. Unit tests need no database.
- **Factories are plain functions** (`tests/factories.py`), not polyfactory: our CHECK constraints make
  randomly generated rows invalid almost every time, so we would override most fields anyway.
- **Dependabot** keeps GitHub Actions and Python dependencies fresh (weekly, grouped).
- Docker image: multi-stage, locked dependencies, non-root, no dev tools.

## Consequences
A failing check is a real signal. If a tool blocks you, fix the cause or discuss changing the rule here;
do not bypass it.
