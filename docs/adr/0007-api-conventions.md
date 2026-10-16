# ADR-0007: API conventions
- Status: Accepted
- Date: 2026-10-16

## Decision
- **Errors** use RFC 9457 `application/problem+json`: `type` (`urn:skincare:problem:<code>`),
  `title`, `status`, `detail`, `instance`, `request_id`, and `errors` for validation failures.
  Services raise subclasses of `AppError` (`app/core/errors.py`); handlers live in `app/api/error_handlers.py`.
  The app switches on `type`, never on `detail`. Unexpected errors return a generic body (no internals).
- **Request IDs**: every response carries `X-Request-ID` (a sane incoming value is kept, otherwise generated);
  every log line of that request includes it. Users can quote it in bug reports.
- **Logging** is structured: JSON outside local development, readable console locally.
- **Pagination** is keyset (cursor) based, never offset, so deep pages stay fast and results stay stable.
- **Versioning**: everything lives under `/api/v1`; health probes are outside it (`/health/live`, `/health/ready`).
- **Contract**: FastAPI's OpenAPI schema is the contract. The mobile app generates its typed client from it;
  CI will fail if the exported schema changes without being committed.

## Consequences
Every endpoint declares its error responses (`responses={404: {"model": ProblemDetails}}`)
so they appear in the generated client.
