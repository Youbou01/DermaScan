# Skincare backend

FastAPI + PostgreSQL, built as a **modular monolith** (one deployable app, strictly separated modules).

## Prerequisites
- [uv](https://docs.astral.sh/uv/) (installs Python 3.14 and dependencies for you)
- Docker Desktop (for the local PostgreSQL)

## First-time setup (about 5 minutes)
```bash
cd backend
uv sync                          # creates .venv, installs everything from uv.lock
cp .env.example .env             # then edit: replace CHANGE_ME (twice) with a password
docker compose up -d db          # starts PostgreSQL 18 on localhost:5432
uv run alembic upgrade head      # creates all tables
uv run uvicorn app.main:create_app --factory --reload
```
Open http://localhost:8000/docs. `GET /health/ready` should return `{"status":"ok"}`.

## Daily commands
| Task | Command |
|---|---|
| Run the API | `uv run uvicorn app.main:create_app --factory --reload` |
| Tests | `uv run pytest` |
| Lint + format | `uv run ruff check . --fix && uv run ruff format .` |
| Type check | `uv run mypy` |
| Architecture rules | `uv run lint-imports` |
| Add a dependency | `uv add <package>` (`uv add --dev <package>` for tooling) |
| Never use | `pip install` (it bypasses `uv.lock`) |

Before every push, these four must pass: `pytest`, `ruff check`, `mypy`, `lint-imports`.

## Database migrations (Alembic)
```bash
uv run alembic revision --autogenerate -m "add something"   # after changing a model
# READ the generated file in migrations/versions/ and fix it if needed. Never trust it blindly.
uv run alembic upgrade head      # apply
uv run alembic downgrade -1      # undo the last one
uv run alembic check             # fails if models and migrations are out of sync
```
Rules: one migration per model change, committed with the model change. Never edit a migration that is already on `main`; add a new one.
A new module with models must be imported in `migrations/env.py`.

## Layout
```
src/app/
  main.py            app factory
  core/              config, DB plumbing, shared enums (cross-cutting only)
  api/               deps + router aggregation (no business logic)
  modules/
    ingredients/     ingredient dictionary, aliases, parsing/normalization
    scoring/         pure scoring algorithm (no tables)
    catalog/         products, brands, categories, search, home feed
    ingestion/       Open Beauty Facts importer, seed loaders
migrations/          Alembic
tests/               unit/ (no DB) and integration/ (real PostgreSQL)
```

## Architecture rules (checked by `lint-imports`)[to check if its respected run `lint-imports`]
1. **One door per module.** Other modules may only import a module's public interface (its `__init__.py`: services and DTOs), never its `models` or `repository`.
2. **Dependencies point down:** `ingestion → catalog → ingredients | scoring → core`. No cycles, no sideways imports between `ingredients` and `scoring`.
3. **Each module owns its tables.** Cross-module foreign keys are fine in the database, but there is no `relationship()` across modules and no cross-module joins. Ask the other module's service.
4. **Inside a module:** `router → service → repository → models`. Routers have no logic, services have no SQL.
5. **Relationships are `lazy="raise"`.** Load what you need explicitly with `selectinload()` in the repository.

## Data conventions
- Primary keys are UUIDv7. Enums are stored as VARCHAR with a CHECK constraint (`enum_type` + `enum_check` in `core/orm.py`).
- `unknown` risk is never treated as safe. Scores are precomputed and stored with `scoring_version`.
- Barcodes are normalized to GTIN-13 before reaching the database.
- Secrets only come from environment variables. `.env` is git-ignored; `.env.example` documents every variable.
