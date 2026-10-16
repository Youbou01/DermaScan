"""Cross-cutting infrastructure only: config, database plumbing, shared vocabulary.

Nothing in here may import from `app.modules`, `app.api` or `app.main`
(enforced by import-linter).
"""
