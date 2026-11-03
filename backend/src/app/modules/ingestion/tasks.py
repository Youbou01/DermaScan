import hashlib
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import enqueue_job, enqueue_singleton_job, register_task
from app.modules.catalog import (
    CatalogService,
    EnrichmentStatus,
    ImageStatus,
    ProductSource,
    ProductUpsert,
    compute_check_digit,
    normalize_gtin,
)
from app.modules.enrichment import EnrichmentService
from app.modules.ingestion.enums import RawProductSource
from app.modules.ingestion.mapper import map_obf_record
from app.modules.ingestion.service import IngestionService
from app.modules.ingestion.sources.base import RawRecord, compute_content_hash
from app.modules.ingestion.sources.obf import (
    OBFSourceAdapter,
    store_raw_product,
)
from app.modules.ingestion.sources.scraper import (
    GenericScraperAdapter,
    ScraperFetchError,
    load_site_config,
)
from app.modules.ingredients import IngredientService

logger = structlog.get_logger(__name__)


def generate_synthetic_gtin13(source: str, source_id: str) -> str:
    digest = hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()
    nine_digits = f"{int(digest[:12], 16) % 1_000_000_000:09d}"
    body12 = f"200{nine_digits}"
    return body12 + str(compute_check_digit(body12))


@register_task("enrich_raw_product")
async def enrich_raw_product_task(payload: dict[str, Any], session: AsyncSession) -> None:
    raw_id_str = payload.get("raw_product_id")
    if not raw_id_str:
        logger.warning("enrich_raw_product_missing_id")
        return

    run_id_str = payload.get("run_id")
    run_id = uuid.UUID(run_id_str) if run_id_str else None
    force_publish = bool(payload.get("force_publish"))

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

    raw_barcode = mapped_dict.get("barcode")
    if raw_barcode:
        try:
            mapped_dict["barcode"] = normalize_gtin(str(raw_barcode))
        except Exception:
            mapped_dict["barcode"] = generate_synthetic_gtin13(raw.source.value, raw.source_id)
    else:
        mapped_dict["barcode"] = generate_synthetic_gtin13(raw.source.value, raw.source_id)

    enrichment_service = EnrichmentService(session)

    if not mapped_dict.get("raw_ingredients_text") or raw.payload.get("has_verified_inci") is False:
        web_ctx = await enrichment_service.fetch_web_context_for_product(
            barcode=mapped_dict["barcode"],
            name=mapped_dict.get("name"),
        )
        if web_ctx:
            mapped_dict.update(web_ctx)

    outcome = await enrichment_service.enrich_product(mapped_dict, raw_payload=raw.payload)

    is_llm_error = (
        outcome.status == EnrichmentStatus.FAILED
        and outcome.reason
        and outcome.reason.startswith("llm_error:")
    )
    if is_llm_error:
        await CatalogService(session).mark_enrichment_failed_by_barcode(mapped_dict["barcode"])
        if run_id:
            await ingestion_service.increment_run_counter(run_id, "failed", 1)
        await session.flush()
        raise RuntimeError(outcome.reason)

    if outcome.status == EnrichmentStatus.QUARANTINED and not force_publish:
        await ingestion_service.quarantine(
            raw_product_id=raw.id,
            stage="enrichment",
            reason=outcome.reason or "unknown_quarantine",
            payload=raw.payload,
        )
        if run_id:
            await ingestion_service.increment_run_counter(run_id, "quarantined", 1)
        await session.flush()
        logger.info("enrich_raw_product_quarantined", raw_id=raw_id_str, reason=outcome.reason)
        return

    if outcome.status == EnrichmentStatus.FAILED and not force_publish:
        logger.info("enrich_raw_product_failed", raw_id=raw_id_str, reason=outcome.reason)
        if outcome.reason == "not_skincare":
            await ingestion_service.quarantine(
                raw_product_id=raw.id,
                stage="enrichment",
                reason="not_skincare",
                payload=raw.payload,
            )
        if run_id:
            await ingestion_service.increment_run_counter(run_id, "failed", 1)
        await session.flush()
        return

    if (outcome.status == EnrichmentStatus.DONE or force_publish) and outcome.result is not None:
        res = outcome.result
        ingredient_service = IngredientService(session)

        # Ensure all LLM-cleaned ingredients exist in DB and alias table before matching
        await ingredient_service.ensure_ingredients_exist(
            [item.model_dump() for item in res.ingredients_inci]
        )

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

        if mapped_dict.get("image_url") or mapped_dict.get("web_image_url"):
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
        if dedupe.match_status == "ambiguous" and not force_publish:
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
            if run_id:
                await ingestion_service.increment_run_counter(run_id, "quarantined", 1)
            await session.flush()
            logger.info(
                "enrich_raw_product_quarantined_ambiguous_duplicate",
                raw_id=raw_id_str,
                matched_id=str(dedupe.product_id),
                similarity=dedupe.similarity,
            )
            return

        final_image_url = mapped_dict.get("image_url") or mapped_dict.get("web_image_url")

        upsert_dto = ProductUpsert(
            barcode=str(mapped_dict.get("barcode") or raw.source_id),
            name=res.name_clean or str(mapped_dict.get("name")),
            source=catalog_source,
            source_id=raw.source_id,
            source_lang=res.source_lang or mapped_dict.get("source_lang"),
            name_i18n=res.name_i18n,
            brand_name=res.brand or mapped_dict.get("brand_name"),
            category_slug=res.category_slug or mapped_dict.get("category_slug"),
            image_url=final_image_url,
            image_source_url=final_image_url,
            raw_ingredients_text=str(mapped_dict.get("raw_ingredients_text") or ""),
            ingredients=ingredients_tuples,
            field_provenance=provenance,
            enrichment_status=EnrichmentStatus.DONE,
        )

        product = await catalog_service.upsert_product(upsert_dto)

        # Enqueue recompute dirty scores via singleton job
        await enqueue_singleton_job(
            session,
            task_name="recompute_dirty_scores",
            payload={"batch_size": 500},
            queue="default",
        )

        # If any matched ingredient is unrated, enqueue rate_ingredients
        matched_ids = [m.ingredient_id for m in matches if m.ingredient_id is not None]
        if matched_ids:
            infos = await ingredient_service.get_many(matched_ids, locale="en")
            if any(info.rating is None for info in infos.values()):
                await enqueue_singleton_job(
                    session,
                    task_name="rate_ingredients",
                    payload={"batch_size": 100},
                    queue="default",
                )

        if run_id:
            await ingestion_service.increment_run_counter(run_id, "published", 1)

        needs_image = product.image_status in (ImageStatus.NONE, ImageStatus.CANDIDATE)
        if product.image_source_url and needs_image:
            await enqueue_job(
                session,
                queue="enrichment",
                task_name="process_product_image",
                payload={"product_id": str(product.id)},
            )

        await session.flush()
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
    adapter = GenericScraperAdapter(site_config=config)
    ingestion_service = IngestionService(session)

    try:
        extracted = await adapter.fetch(url, config=config)
    except (ScraperFetchError, Exception) as exc:
        logger.warning("scrape_url_fetch_failed", url=url, error=str(exc))
        await ingestion_service.stage_scrape(
            url=url,
            status="failed",
            content_hash="",
            extracted_json={},
            run_id=run_id,
        )
        if run_id:
            await ingestion_service.increment_run_counter(run_id, "failed", 1)
        await session.flush()
        raise

    if not extracted or not (extracted.get("name") or extracted.get("barcode")):
        logger.warning("scrape_url_failed_extraction", url=url)
        await ingestion_service.stage_scrape(
            url=url,
            status="failed",
            content_hash="",
            extracted_json=extracted or {},
            run_id=run_id,
        )
        if run_id:
            await ingestion_service.increment_run_counter(run_id, "failed", 1)
        await session.flush()
        raise RuntimeError(f"Failed extraction for {url}")

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
            queue="enrichment",
            task_name="enrich_raw_product",
            payload={"raw_product_id": str(raw_id), "run_id": str(run_id) if run_id else None},
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
            queue="enrichment",
            task_name="enrich_raw_product",
            payload={"raw_product_id": str(raw_id)},
        )
        logger.info("import_obf_barcode_enqueued_enrichment", barcode=barcode, raw_id=str(raw_id))
    else:
        logger.info("import_obf_barcode_already_stored", barcode=barcode)


@register_task("backfill_pending_products")
async def backfill_pending_products_task(payload: dict[str, Any], session: AsyncSession) -> None:
    batch_size = int(payload.get("batch_size") or 200)
    catalog_service = CatalogService(session)
    claimed = await catalog_service.claim_products_for_backfill(batch_size=batch_size)
    if not claimed:
        return

    for item in claimed:
        raw_payload = {
            "barcode": item["barcode"],
            "code": item["barcode"],
            "product_name": item["name"],
            "raw_ingredients_text": item["raw_ingredients_text"],
            "image_url": item["image_url"],
        }
        raw_rec = RawRecord(
            source=item["source"],
            source_id=item["barcode"],
            content_hash=compute_content_hash(raw_payload),
            payload=raw_payload,
            url=item["image_url"],
        )
        raw_id = await store_raw_product(session, raw_rec)
        if raw_id is not None:
            await enqueue_job(
                session,
                queue="enrichment",
                task_name="enrich_raw_product",
                payload={"raw_product_id": str(raw_id)},
            )
        if item["image_status"] == ImageStatus.NONE and item["image_url"]:
            await enqueue_job(
                session,
                queue="enrichment",
                task_name="process_product_image",
                payload={"product_id": str(item["id"])},
            )

    if len(claimed) == batch_size:
        await enqueue_singleton_job(
            session,
            task_name="backfill_pending_products",
            payload={"batch_size": batch_size},
            queue="default",
        )
