import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import enqueue_job, register_task
from app.modules.catalog import CatalogService, ProductUpsert
from app.modules.catalog.enums import EnrichmentStatus, ImageStatus, ProductSource
from app.modules.enrichment import EnrichmentService
from app.modules.ingestion.enums import RawProductSource
from app.modules.ingestion.mapper import map_obf_record
from app.modules.ingestion.service import IngestionService
from app.modules.ingredients import IngredientService

logger = structlog.get_logger(__name__)


@register_task("enrich_raw_product")
async def enrich_raw_product_task(payload: dict[str, Any], session: AsyncSession) -> None:
    raw_id_str = payload.get("raw_product_id")
    if not raw_id_str:
        logger.warning("enrich_raw_product_missing_id")
        return

    raw_id = uuid.UUID(raw_id_str)
    ingestion_service = IngestionService(session)
    raw = await ingestion_service.get_raw_product(raw_id)
    if raw is None:
        logger.warning("enrich_raw_product_not_found", raw_id=raw_id_str)
        return

    mapped_dict: dict[str, Any]
    if raw.source == RawProductSource.OPEN_BEAUTY_FACTS:
        mapped_obj = map_obf_record(raw.payload)
        mapped_dict = {
            "barcode": mapped_obj.barcode,
            "name": mapped_obj.name,
            "brand_name": mapped_obj.primary_brand,
            "category_slug": mapped_obj.category_slug,
            "raw_ingredients_text": mapped_obj.raw_ingredients_text,
            "source_lang": mapped_obj.source_lang,
            "image_url": mapped_obj.image_url,
        }
    else:
        mapped_dict = dict(raw.payload)

    enrichment_service = EnrichmentService(session)
    outcome = await enrichment_service.enrich_product(mapped_dict, raw_payload=raw.payload)

    if outcome.status == EnrichmentStatus.QUARANTINED:
        await ingestion_service.quarantine(
            raw_product_id=raw.id,
            stage="enrichment",
            reason=outcome.reason or "unknown_quarantine",
            payload=raw.payload,
        )
        logger.info("enrich_raw_product_quarantined", raw_id=raw_id_str, reason=outcome.reason)
        return

    if outcome.status == EnrichmentStatus.FAILED:
        logger.info("enrich_raw_product_failed", raw_id=raw_id_str, reason=outcome.reason)
        if outcome.reason == "not_skincare":
            await ingestion_service.quarantine(
                raw_product_id=raw.id,
                stage="enrichment",
                reason="not_skincare",
                payload=raw.payload,
            )
        return

    if outcome.status == EnrichmentStatus.DONE and outcome.result is not None:
        res = outcome.result
        ingredient_service = IngredientService(session)
        names_to_match = [item.inci or item.original for item in res.ingredients_inci]
        matches = await ingredient_service.match(names_to_match)

        ingredients_tuples: list[tuple[int, str, uuid.UUID | None]] = []
        for idx, (item, match) in enumerate(
            zip(res.ingredients_inci, matches, strict=True), start=1
        ):
            ingredients_tuples.append((idx, item.original, match.ingredient_id))

        provenance: dict[str, Any] = {
            "name": {"source": "ai", "confidence": 0.9},
            "ingredients": {"source": "ai", "confidence": res.ingredients_confidence},
        }
        if res.brand:
            provenance["brand"] = {"source": "ai", "confidence": res.brand_confidence}
        elif mapped_dict.get("brand_name"):
            provenance["brand"] = {"source": raw.source.value, "confidence": 1.0}

        if res.category_slug:
            provenance["category"] = {"source": "ai", "confidence": res.category_confidence}
        elif mapped_dict.get("category_slug"):
            provenance["category"] = {"source": raw.source.value, "confidence": 1.0}

        if mapped_dict.get("image_url"):
            provenance["image"] = {"source": raw.source.value, "confidence": 1.0}

        catalog_source = (
            ProductSource.OPEN_BEAUTY_FACTS
            if raw.source == RawProductSource.OPEN_BEAUTY_FACTS
            else ProductSource.MANUAL
        )

        upsert_dto = ProductUpsert(
            barcode=str(mapped_dict.get("barcode") or raw.source_id),
            name=res.name_clean or str(mapped_dict.get("name")),
            source=catalog_source,
            source_id=raw.source_id,
            source_lang=res.source_lang or mapped_dict.get("source_lang"),
            name_i18n=res.name_i18n,
            brand_name=res.brand or mapped_dict.get("brand_name"),
            category_slug=res.category_slug or mapped_dict.get("category_slug"),
            image_url=mapped_dict.get("image_url"),
            image_source_url=mapped_dict.get("image_url"),
            raw_ingredients_text=str(mapped_dict.get("raw_ingredients_text") or ""),
            ingredients=ingredients_tuples,
            field_provenance=provenance,
            enrichment_status=EnrichmentStatus.DONE,
        )

        catalog_service = CatalogService(session)
        product = await catalog_service.upsert_product(upsert_dto)

        # Enqueue recompute dirty scores
        await enqueue_job(
            session,
            queue="default",
            task_name="recompute_dirty_scores",
            payload={"batch_size": 100},
        )

        needs_image = product.image_status in (ImageStatus.NONE, ImageStatus.CANDIDATE)
        if product.image_source_url and needs_image:
            await enqueue_job(
                session,
                queue="default",
                task_name="process_product_image",
                payload={"product_id": str(product.id)},
            )

        logger.info(
            "enrich_raw_product_published",
            product_id=str(product.id),
            barcode=product.barcode,
        )
