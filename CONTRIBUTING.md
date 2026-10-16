# Contributing

## Workflow
1. Pick a task, create a branch from `main`: `feat/short-name`, `fix/short-name`, `chore/short-name`.
2. Commit small and often using [Conventional Commits](https://www.conventionalcommits.org/):
   `feat(catalog): add barcode lookup endpoint`, `fix(ingredients): handle empty label`, `chore: bump deps`.
3. Open a Pull Request into `main`. Keep it small (aim for under ~400 changed lines) and fill in the template.
4. CI must be green and **one teammate must approve**. Merge with **Squash and merge**.
5. Never push directly to `main`, never force-push a shared branch.

## One-time setup (every developer)
```bash
cd backend
uv sync
cp .env.example .env            # set the passwords
docker compose up -d db
uv run alembic upgrade head
uv run pre-commit install       # checks run automatically on every commit
```

## What runs on every commit / PR
| Check | Command | What it catches |
|---|---|---|
| Lint + format | `ruff check` / `ruff format` | bugs, style, missing type hints, insecure patterns |
| Types | `mypy` (strict) | type errors, wrong signatures |
| Architecture | `lint-imports` | a module reaching into another module's internals |
| Migrations | `alembic upgrade head`, `alembic check` | model changed without a migration |
| Tests | `pytest` | regressions (integration tests use a real PostgreSQL) |

If pre-commit rewrites files (formatting), re-stage them and commit again.
Do **not** bypass hooks with `--no-verify`: CI runs the same checks and will fail anyway.

## Definition of done
- [ ] Works, and the acceptance criteria of the story are met
- [ ] Tests: unit tests for logic, integration tests for endpoints and queries; bug fixes include a test that failed before
- [ ] Type hints on every function signature
- [ ] Model change has a migration, and you **read** the generated migration
- [ ] No secrets in code or git; every new setting is in `Settings` and `.env.example`
- [ ] Errors use the shared exception classes (`app/core/errors.py`), never raw `HTTPException` in services
- [ ] Public API change is mentioned in the PR (the mobile app depends on it)
- [ ] A decision that future developers will question gets a short ADR in `docs/adr/`

## Adding an endpoint (the usual path)
1. Put logic in the module's `service.py`; SQL in its `repository.py`; request/response models in `schemas.py`.
2. Raise module exceptions (subclasses of `app/core/errors.py`) such as `ProductNotFoundError`.
3. Expose it in the module's `router.py`, declare error responses with `responses={404: {"model": ProblemDetails}}`, and mount the router in `app/api/v1/router.py`.
4. Test it through the `client` fixture (`tests/integration/`) and test the logic without a database (`tests/unit/`).
5. Another module needs your data? Export a service function + DTO from your module's `__init__.py`. Never import its models.

## GitHub settings to enable once (repository owner)
Settings → Branches → rule for `main`: require a pull request, require 1 approval, require the
status check **Backend CI / checks**, require branches to be up to date, block force pushes.
Settings → General → Pull Requests: allow squash merging only, auto-delete head branches.
