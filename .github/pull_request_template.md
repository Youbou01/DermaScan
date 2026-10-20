## What and why
<!-- One or two sentences. Link the task/user story. -->

## How to test
<!-- Commands or steps a reviewer can run. -->

## Checklist
- [ ] Backend: `ruff`, `mypy`, `lint-imports` and `pytest` pass locally (pre-commit runs the first three)
- [ ] Mobile: `npm run check` passes, and a screen recording from a real device is attached
- [ ] New behaviour has tests (unit for logic, integration for endpoints/queries)
- [ ] Model change → migration included, and I read the generated migration
- [ ] No secrets, no `.env`, no new environment variable missing from `.env.example`
- [ ] Public API change → noted below (the mobile app depends on it)

## API contract changes
<!-- "None", or describe added/changed/removed endpoints and fields. -->
