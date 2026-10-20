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

### Mobile (only if you touch `mobile/`)
```bash
cd mobile
npm install && npx expo install --fix && npm run check
cp .env.example .env            # set EXPO_PUBLIC_API_URL, see mobile/README.md
```
Full guide: `mobile/README.md`. Rules for people and AI assistants: `mobile/AGENTS.md`.

## What runs on every commit / PR
| Check | Command | What it catches |
|---|---|---|
| Lint + format | `ruff check` / `ruff format` | bugs, style, missing type hints, insecure patterns |
| Types | `mypy` (strict) | type errors, wrong signatures |
| Architecture | `lint-imports` | a module reaching into another module's internals |
| Migrations | `alembic upgrade head`, `alembic check` | model changed without a migration |
| Tests | `pytest` | regressions (integration tests use a real PostgreSQL) |

Mobile (`mobile/`): `npm run check` = typecheck + ESLint + Prettier + Jest, run by pre-commit and by
the **Mobile CI** workflow.

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
- [ ] Mobile PRs: `npm run check` is green and a screen recording from a real device is attached
- [ ] A decision that future developers will question gets a short ADR in `docs/adr/`

## Adding an endpoint (the usual path)
1. Put logic in the module's `service.py`; SQL in its `repository.py`; request/response models in `schemas.py`.
2. Raise module exceptions (subclasses of `app/core/errors.py`) such as `ProductNotFoundError`.
3. Expose it in the module's `router.py` (use `SessionDep` / `LocaleDep` from `app/core/dependencies.py`), declare error responses with `responses={404: {"model": ProblemDetails}}`, export the router from the module's `__init__.py` as `<module>_router`, and mount it in `app/api/v1/router.py`.
4. Test it through the `client` fixture (`tests/integration/`) and test the logic without a database (`tests/unit/`).
5. Another module needs your data? Export a service function + DTO from your module's `__init__.py`. Never import its models.

## Trying the API with data
`uv run python scripts/seed_demo.py` inserts a few demo ingredients and products (safe to run twice), e.g.
barcode `6190000000019`: `GET http://localhost:8000/api/v1/products/by-barcode/6190000000019`.
It is a stop-gap: the real seed loader and importer replace it.

## GitHub settings to enable once (repository owner)
Settings → Branches → rule for `main`: require a pull request, require 1 approval, require the
status checks **Backend CI / checks** and **Mobile CI / checks**, require branches to be up to date, block force pushes.
Settings → General → Pull Requests: allow squash merging only, auto-delete head branches.
