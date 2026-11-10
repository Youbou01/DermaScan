"""HTTP boundary for signed-in, instant ingredient-label analysis."""

from io import BytesIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.security import CurrentUserIdDep
from app.modules.enrichment.exceptions import (
    AnalysisImageTooLargeError,
    UnreadableAnalysisImageError,
    UnsupportedAnalysisImageError,
)
from app.modules.enrichment.schemas import InstantAnalysisOut, TextAnalysisIn
from app.modules.enrichment.service import EnrichmentService

router = APIRouter()

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails},
    413: {"model": ProblemDetails},
    415: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
}


def get_enrichment_service(session: SessionDep, request: Request) -> EnrichmentService:
    """Use the app's settings so test-mode requests use the deterministic LLM client."""
    return EnrichmentService(session, settings=request.app.state.settings)


ServiceDep = Annotated[EnrichmentService, Depends(get_enrichment_service)]


@router.post("/ocr", response_model=InstantAnalysisOut, responses=_ERRORS)
async def analyze_ocr_photo(
    photo: Annotated[UploadFile, File(description="JPEG, PNG, or WebP ingredient-label photo.")],
    service: ServiceDep,
    session: SessionDep,
    locale: LocaleDep,
    user_id: CurrentUserIdDep,
    product_name: Annotated[str | None, Form(max_length=255)] = None,
) -> InstantAnalysisOut:
    """Transcribe and analyse an unlisted product label in the request/response cycle."""
    del user_id  # Authentication gates this personal workflow; no user data is persisted here.
    photo_bytes = await _validated_image_bytes(photo)
    ocr = await service.ocr_ingredients(photo_bytes)
    if not ocr.is_readable or not ocr.ingredients_text.strip():
        raise UnreadableAnalysisImageError("Retake the photo with the ingredient label in focus.")

    analysis = await service.analyze_ingredient_label(
        ocr.ingredients_text,
        locale=locale,
        product_name=product_name,
    )
    # The LLM gateway stores cache and usage records as part of a successful analysis.
    await session.commit()
    return analysis


@router.post("/text", response_model=InstantAnalysisOut, responses=_ERRORS)
async def analyze_ingredient_text(
    data: TextAnalysisIn,
    service: ServiceDep,
    session: SessionDep,
    locale: LocaleDep,
    user_id: CurrentUserIdDep,
) -> InstantAnalysisOut:
    """Analyse manually pasted ingredients with the same matching and scoring pipeline."""
    del user_id
    analysis = await service.analyze_ingredient_label(
        data.text,
        locale=locale,
        product_name=data.product_name,
    )
    await session.commit()
    return analysis


async def _validated_image_bytes(photo: UploadFile) -> bytes:
    """Bound OCR input size and verify its real image format, not only its HTTP header."""
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedAnalysisImageError("Use a JPEG, PNG, or WebP image.")

    photo_bytes = await photo.read(MAX_IMAGE_BYTES + 1)
    if not photo_bytes:
        raise UnreadableAnalysisImageError("The uploaded image is empty.")
    if len(photo_bytes) > MAX_IMAGE_BYTES:
        raise AnalysisImageTooLargeError("Ingredient-label images must be 10 MB or smaller.")

    try:
        with Image.open(BytesIO(photo_bytes)) as image:
            image_format = image.format
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        raise UnsupportedAnalysisImageError("Use a valid JPEG, PNG, or WebP image.") from exc

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise UnsupportedAnalysisImageError("Use a JPEG, PNG, or WebP image.")
    return photo_bytes
