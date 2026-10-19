"""Catalog errors. The `code` becomes the problem `type` the mobile app switches on:
urn:skincare:problem:<code>."""

from app.core.errors import NotFoundError, UnprocessableError


class InvalidBarcodeError(UnprocessableError):
    code = "invalid-barcode"
    title = "Invalid barcode"


class ProductNotFoundError(NotFoundError):
    code = "product-not-found"
    title = "Product not found"
