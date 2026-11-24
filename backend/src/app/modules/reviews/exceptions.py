"""Domain errors for the reviews module."""

from app.core.errors import ConflictError


class DuplicateReviewError(ConflictError):
    code = "duplicate-review"
    title = "You have already reviewed this product"
