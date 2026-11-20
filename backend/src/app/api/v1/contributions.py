import uuid
from io import BytesIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session
from app.core.errors import ProblemDetails
from app.core.jobs import enqueue_job
from app.core.storage import get_storage_client
from app.modules.catalog import normalize_gtin
from app.modules.enrichment import EnrichmentService
from app.modules.ingestion import (
    IngestionService,
    RawProductSource,
    RawRecord,
    compute_content_hash,
    store_raw_product,
)

router = APIRouter()

MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


async def _validated_photo(photo: UploadFile) -> tuple[bytes, str, str]:
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG, or WebP photo.")
    photo_bytes = await photo.read(MAX_PHOTO_SIZE + 1)
    if not photo_bytes:
        raise HTTPException(status_code=400, detail="Uploaded photo file is empty.")
    if len(photo_bytes) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=413, detail="Photo file exceeds 10MB limit.")
    try:
        with Image.open(BytesIO(photo_bytes)) as image:
            image_format = image.format
            image.verify()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise HTTPException(
            status_code=415, detail="Use a valid JPEG, PNG, or WebP photo."
        ) from exc
    if image_format is None or image_format not in IMAGE_FORMATS:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG, or WebP photo.")
    extension, content_type = IMAGE_FORMATS[image_format]
    return photo_bytes, extension, content_type


class ContributionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    barcode: str
    status: str
    message: str


@router.post(
    "",
    response_model=ContributionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={code: {"model": ProblemDetails} for code in (400, 413, 415, 422)},
)
async def submit_photo_contribution(
    barcode: Annotated[str, Form(description="Product barcode (GTIN-8, GTIN-12, or GTIN-13)")],
    photo: Annotated[UploadFile, File(description="Photo of product packaging ingredient label")],
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> dict[str, Any]:
    # 1. Validate barcode
    try:
        norm_barcode = normalize_gtin(barcode)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid barcode: {exc}",
        ) from exc

    # Validate bounded input and preserve its actual detected image format.
    photo_bytes, extension, content_type = await _validated_photo(photo)

    # 3. Store photo securely
    file_id = uuid.uuid7()
    storage = get_storage_client()
    path = f"contributions/{file_id}.{extension}"
    image_url = await storage.put_image(path, photo_bytes, content_type)

    # 4. Vision OCR via EnrichmentService
    settings = getattr(request.app.state, "settings", None)
    enrichment = EnrichmentService(session, settings=settings)
    ocr = await enrichment.ocr_ingredients(photo_bytes)

    # 5. Store raw_product record
    payload = {
        "barcode": norm_barcode,
        "name": f"Product {norm_barcode}",
        "raw_ingredients_text": ocr.ingredients_text,
        "image_url": image_url,
        "ocr_confidence": ocr.confidence,
    }
    raw_rec = RawRecord(
        source=RawProductSource.USER_PHOTO.value,
        source_id=norm_barcode,
        content_hash=compute_content_hash(payload),
        payload=payload,
        url=image_url,
    )
    raw_id = await store_raw_product(session, raw_rec)

    # 6. Route to enrichment or quarantine based on OCR quality
    is_high_quality = ocr.confidence >= 0.7 and ocr.is_readable and len(ocr.ingredients_text) >= 10

    if is_high_quality:
        if raw_id:
            await enqueue_job(
                session,
                queue="enrichment",
                task_name="enrich_raw_product",
                payload={"raw_product_id": str(raw_id)},
            )
        await session.commit()
        return {
            "id": file_id,
            "barcode": norm_barcode,
            "status": "processing",
            "message": "Photo received and ingredients transcribed. Product is being enriched.",
        }

    ingestion = IngestionService(session)
    await ingestion.quarantine(
        raw_product_id=raw_id,
        stage="user_photo_ocr",
        reason="user_photo_low_confidence",
        payload={
            "barcode": norm_barcode,
            "text": ocr.ingredients_text,
            "confidence": ocr.confidence,
            "image_url": image_url,
        },
    )
    await session.commit()
    return {
        "id": file_id,
        "barcode": norm_barcode,
        "status": "quarantined",
        "message": (
            "Photo received, but ingredient label was low confidence or unreadable. Queued for human review."
        ),
    }
