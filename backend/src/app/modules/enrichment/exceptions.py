"""Domain errors raised by the enrichment module."""

from app.core.errors import AppError, UnprocessableError


class NoAnalyzableIngredientsError(UnprocessableError):
    """The submitted label did not contain an ingredient token we can analyse."""

    code = "no-analyzable-ingredients"
    title = "No analysable ingredients found"


class UnreadableAnalysisImageError(UnprocessableError):
    """The OCR provider could not read an ingredient label from the image."""

    code = "unreadable-ingredient-label"
    title = "Ingredient label could not be read"


class UnsupportedAnalysisImageError(AppError):
    """The submitted file is not one of the image types accepted by OCR."""

    status_code = 415
    code = "unsupported-ingredient-image"
    title = "Unsupported ingredient-label image"


class AnalysisImageTooLargeError(AppError):
    """The image would exceed the bounded OCR request payload."""

    status_code = 413
    code = "ingredient-image-too-large"
    title = "Ingredient-label image is too large"
