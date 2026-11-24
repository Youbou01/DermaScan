"""RFC 9457 errors raised by routine services."""

from app.core.errors import NotFoundError, UnprocessableError


class RoutineNotFoundError(NotFoundError):
    code = "routine-not-found"
    title = "Routine not found"


class RoutineProductNotFoundError(NotFoundError):
    code = "routine-product-not-found"
    title = "Routine product not found"


class InvalidRoutineStepsError(UnprocessableError):
    code = "invalid-routine-steps"
    title = "Routine steps are invalid"


class RoutineShareLinkNotFoundError(NotFoundError):
    code = "routine-share-link-not-found"
    title = "Shared routine link not found"


class EmptyRoutineShareError(UnprocessableError):
    code = "empty-routine-share"
    title = "An empty routine cannot be shared"
