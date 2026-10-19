"""Catalog errors. The `code` becomes the problem `type` the mobile app switches on:
urn:skincare:problem:<code>."""

from app.core.errors import BadRequestError, NotFoundError, UnprocessableError


class InvalidBarcodeError(UnprocessableError):
    code = "invalid-barcode"
    title = "Invalid barcode"


class ProductNotFoundError(NotFoundError):
    code = "product-not-found"
    title = "Product not found"


class InvalidCursorError(BadRequestError):
    code = "invalid-cursor"
    title = "Invalid cursor"


class InvalidLimitError(BadRequestError):
    code = "invalid-limit"
    title = "Invalid limit"


class SectionNotFoundError(NotFoundError):
    code = "section-not-found"
    title = "Home section not found"
