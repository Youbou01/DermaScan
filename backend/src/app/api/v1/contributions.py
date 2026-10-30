import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session
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


class ContributionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    barcode: str
    status: str
    message: str


@router.post("", response_model=ContributionResponse, status_code=status.HTTP_202_ACCEPTED)
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

    # 2. Validate file type
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{photo.content_type}'. Must be JPEG, PNG, or WebP.",
        )

    # Read and validate size
    photo_bytes = await photo.read()
    if len(photo_bytes) > MAX_PHOTO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Photo file exceeds 10MB limit.",
        )
    if len(photo_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded photo file is empty.",
        )

    # 3. Store photo securely
    file_id = uuid.uuid7()
    storage = get_storage_client()
    path = f"contributions/{file_id}.webp"
    image_url = await storage.put_image(path, photo_bytes, "image/webp")

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
                queue="default",
                task_name="enrich_raw_product",
                payload={"raw_product_id": str(raw_id)},
            )
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
    return {
        "id": file_id,
        "barcode": norm_barcode,
        "status": "quarantined",
        "message": (
            "Photo received, but ingredient label was low confidence or unreadable. "
            "Queued for human review."
        ),
    }
