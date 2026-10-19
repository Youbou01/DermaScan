"""Domain exceptions and the error response shape (RFC 9457 "problem details").

Services raise subclasses of `AppError`; the API layer turns them into
`application/problem+json` responses (see `app/api/error_handlers.py`).
Modules define their own specific errors by subclassing, e.g. in catalog/exceptions.py:

    class ProductNotFoundError(NotFoundError):
        code = "product-not-found"
        title = "Product not found"

The mobile app switches on the response's `type` (derived from `code`), never on `detail`.
"""

from typing import Any, ClassVar

from pydantic import BaseModel


class ProblemDetails(BaseModel):
    """Error body. Declared so it appears in the OpenAPI schema (typed client)."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None  # the request path
    request_id: str | None = None
    errors: list[dict[str, Any]] | None = None  # only for request-validation failures


class AppError(Exception):
    status_code: ClassVar[int] = 500
    code: ClassVar[str] = "internal-error"
    title: ClassVar[str] = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400
    code = "bad-request"
    title = "Bad request"


class NotFoundError(AppError):
    status_code = 404
    code = "not-found"
    title = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    title = "Conflict with the current state of the resource"


class UnprocessableError(AppError):
    """The request is well-formed but breaks a business rule."""

    status_code = 422
    code = "unprocessable"
    title = "Request cannot be processed"


class UpstreamError(AppError):
    """An external service (e.g. Open Beauty Facts) failed or timed out."""

    status_code = 502
    code = "upstream-error"
    title = "An upstream service failed"
