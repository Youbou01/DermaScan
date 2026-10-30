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
from app.modules.ingestion.sources import (
    GenericScraperAdapter,
    OBFSourceAdapter,
    compute_content_hash,
    load_site_config,
    store_raw_product,
)
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

        if raw.source == RawProductSource.OPEN_BEAUTY_FACTS:
            catalog_source = ProductSource.OPEN_BEAUTY_FACTS
        elif raw.source == RawProductSource.SCRAPE:
            catalog_source = ProductSource.SCRAPE
        elif raw.source == RawProductSource.USER_PHOTO:
            catalog_source = ProductSource.USER_PHOTO
        else:
            catalog_source = ProductSource.MANUAL

        catalog_service = CatalogService(session)
        dedupe = await catalog_service.resolve_or_deduplicate(
            barcode=mapped_dict.get("barcode"),
            name=res.name_clean or str(mapped_dict.get("name")),
            brand_name=res.brand or mapped_dict.get("brand_name"),
            source=catalog_source,
            source_id=raw.source_id,
        )
        if dedupe.match_status == "ambiguous":
            await ingestion_service.quarantine(
                raw_product_id=raw.id,
                stage="deduplication",
                reason="ambiguous_duplicate",
                payload={
                    "raw_product_id": str(raw.id),
                    "matched_product_id": str(dedupe.product_id),
                    "similarity": dedupe.similarity,
                    "candidates": [
                        {"id": str(cid), "name": cname, "score": score}
                        for cid, cname, score in dedupe.candidate_matches
                    ],
                },
            )
            logger.info(
                "enrich_raw_product_quarantined_ambiguous_duplicate",
                raw_id=raw_id_str,
                matched_id=str(dedupe.product_id),
                similarity=dedupe.similarity,
            )
            return

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


@register_task("scrape_url")
async def scrape_url_task(payload: dict[str, Any], session: AsyncSession) -> None:
    url = payload.get("url")
    if not url:
        logger.warning("scrape_url_missing_url")
        return

    site_config_name = payload.get("site_config")
    run_id_str = payload.get("run_id")
    run_id = uuid.UUID(run_id_str) if run_id_str else None

    config = load_site_config(site_config_name)
    adapter = GenericScraperAdapter()
    extracted = await adapter.fetch(url, config=config)

    ingestion_service = IngestionService(session)

    if not extracted or not (extracted.get("name") or extracted.get("barcode")):
        logger.warning("scrape_url_failed_extraction", url=url)
        await ingestion_service.stage_scrape(
            url=url,
            status="failed",
            content_hash="",
            extracted_json=extracted or {},
            run_id=run_id,
        )
        return

    content_hash = compute_content_hash(extracted)
    await ingestion_service.stage_scrape(
        url=url,
        status="extracted",
        content_hash=content_hash,
        extracted_json=extracted,
        run_id=run_id,
    )

    raw_rec = adapter.to_raw(extracted, url=url)
    raw_id = await store_raw_product(session, raw_rec)
    if raw_id:
        await enqueue_job(
            session,
            queue="default",
            task_name="enrich_raw_product",
            payload={"raw_product_id": str(raw_id)},
        )
        logger.info("scrape_url_enqueued_enrichment", url=url, raw_id=str(raw_id))
    else:
        logger.info("scrape_url_already_stored", url=url)


@register_task("import_obf_barcode")
async def import_obf_barcode_task(payload: dict[str, Any], session: AsyncSession) -> None:
    barcode = payload.get("barcode")
    if not barcode:
        logger.warning("import_obf_barcode_missing_barcode")
        return

    adapter = OBFSourceAdapter()
    fetched = await adapter.fetch(barcode)
    if not fetched:
        logger.info("import_obf_barcode_not_found", barcode=barcode)
        return

    raw_rec = adapter.to_raw(fetched)
    raw_id = await store_raw_product(session, raw_rec)
    if raw_id:
        await enqueue_job(
            session,
            queue="default",
            task_name="enrich_raw_product",
            payload={"raw_product_id": str(raw_id)},
        )
        logger.info("import_obf_barcode_enqueued_enrichment", barcode=barcode, raw_id=str(raw_id))
    else:
        logger.info("import_obf_barcode_already_stored", barcode=barcode)
