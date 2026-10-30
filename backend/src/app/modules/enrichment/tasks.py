import hashlib
import uuid
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import register_task
from app.core.storage import get_storage_client
from app.modules.catalog import CatalogService
from app.modules.catalog.enums import ImageStatus
from app.modules.enrichment.images import standardize_image, validate_image_candidate
from app.modules.enrichment.service import EnrichmentService

logger = structlog.get_logger(__name__)


@register_task("rate_ingredients")
async def rate_ingredients_task(payload: dict[str, Any], session: AsyncSession) -> None:
    raw_ids = payload.get("ingredient_ids") or []
    ingredient_ids = [uuid.UUID(str(i)) for i in raw_ids]
    if not ingredient_ids:
        logger.info("rate_ingredients_task_empty")
        return

    service = EnrichmentService(session)
    count = await service.rate_ingredients(ingredient_ids)
    logger.info("rate_ingredients_task_finished", rated_count=count)


@register_task("process_product_image")
async def process_product_image_task(payload: dict[str, Any], session: AsyncSession) -> None:
    prod_id_raw = payload.get("product_id")
    if not prod_id_raw:
        logger.warning("process_product_image_missing_id")
        return
    prod_id = uuid.UUID(str(prod_id_raw))

    catalog_service = CatalogService(session)
    info = await catalog_service.get_image_info(prod_id)
    if info is None:
        logger.warning("process_product_image_product_not_found", product_id=str(prod_id))
        return

    barcode, source_url, _ = info
    if not source_url:
        await catalog_service.update_image_result(prod_id, None, ImageStatus.NONE)
        return

    # Fetch candidate image
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(source_url)
            if resp.status_code != 200:
                logger.warning(
                    "candidate_image_fetch_failed", url=source_url, status=resp.status_code
                )
                await catalog_service.update_image_result(prod_id, None, ImageStatus.FAILED)
                return
            img_bytes = resp.content
    except Exception as exc:
        logger.warning("candidate_image_fetch_exception", url=source_url, error=str(exc))
        await catalog_service.update_image_result(prod_id, None, ImageStatus.FAILED)
        return

    # Validate candidate
    is_valid, reason = validate_image_candidate(img_bytes)
    if not is_valid:
        logger.info("candidate_image_invalid", product_id=str(prod_id), reason=reason)
        await catalog_service.update_image_result(prod_id, None, ImageStatus.NONE)
        return

    # Standardize image
    try:
        std = standardize_image(img_bytes)
    except Exception as exc:
        logger.error("image_standardization_failed", product_id=str(prod_id), error=str(exc))
        await catalog_service.update_image_result(prod_id, None, ImageStatus.FAILED)
        return

    # Upload to storage
    sha = hashlib.sha256(img_bytes).hexdigest()[:16]
    key_full = f"products/{barcode}/{sha}.webp"
    key_thumb = f"products/{barcode}/{sha}_thumb.webp"

    storage = get_storage_client()
    full_url = await storage.put_image(key_full, std.full, content_type="image/webp")
    await storage.put_image(key_thumb, std.thumbnail, content_type="image/webp")

    await catalog_service.update_image_result(
        prod_id,
        image_url=full_url,
        image_status=ImageStatus.PROCESSED,
        image_quality=Decimal("0.85"),
    )
    logger.info("process_product_image_success", product_id=str(prod_id), image_url=full_url)
