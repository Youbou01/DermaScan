"""Idempotent, transactional in-place database sanitizer and re-pipelining runner.

Executes 7 cleaning and repipelining steps:
1. Seed curated & gold set ingredients (seed_data.csv + ratings_gold.csv).
2. Purge garbage product_ingredient & ingredient rows and renumber positions contiguously.
3. Quarantine & delete products with < 2 valid ingredients.
4. Clean and merge 'xx:' brand prefixes matching ^[a-zA-Z]{2}:.
5. Repair corrupted ingredient translations.
6. Re-process products with missing or non-CDN images.
7. Reset failed jobs, rate product-linked unrated ingredients, and recompute dirty scores.
"""

import argparse
import asyncio
import logging
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
# Ensure task handlers are registered
from scripts.import_cosing import load_seed_data
from sqlalchemy import and_, delete, func, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import app.modules.catalog.tasks
import app.modules.enrichment.tasks
import app.modules.ingestion.tasks  # noqa: F401
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.jobs import (
    Job,
    JobStatus,
    enqueue_job,
    enqueue_singleton_job,
    run_pending_jobs,
)
from app.modules.catalog import CatalogService
from app.modules.catalog.enums import ImageStatus, ProductSource
from app.modules.catalog.models import Brand, Product, ProductIngredient
from app.modules.enrichment import EnrichmentService
from app.modules.ingestion import IngestionService
from app.modules.ingestion.mapper import _clean_brand_token
from app.modules.ingestion.models import RawProduct
from app.modules.ingredients import IngredientService, is_valid_ingredient_token
from app.modules.ingredients.models import Ingredient, IngredientTranslation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sanitize_and_repipeline")


async def step1_seed_curated_ingredients(session: AsyncSession) -> int:
    """Step 1: Seed curated & gold set ingredients."""
    logger.info("--- Step 1: Seeding curated and gold set ingredients ---")
    count = await load_seed_data(session)
    logger.info("Step 1 complete: %d curated ingredients seeded/verified.", count)
    return count


async def step2_purge_garbage_tokens(session: AsyncSession) -> tuple[int, int]:
    """Step 2: Purge invalid tokens, renumber positions contiguously."""
    logger.info("--- Step 2: Purging garbage tokens and re-numbering product ingredients ---")

    pi_stmt = select(
        ProductIngredient.product_id,
        ProductIngredient.position,
        ProductIngredient.raw_text,
    )
    pi_res = await session.execute(pi_stmt)
    all_pi = pi_res.all()

    invalid_by_product: dict[uuid.UUID, list[int]] = {}
    for pid, pos, raw_text in all_pi:
        if not is_valid_ingredient_token(raw_text):
            invalid_by_product.setdefault(pid, []).append(pos)

    total_purged_pi = 0
    for pid, invalid_positions in invalid_by_product.items():
        total_purged_pi += len(invalid_positions)
        await session.execute(
            delete(ProductIngredient).where(
                ProductIngredient.product_id == pid,
                ProductIngredient.position.in_(invalid_positions),
            )
        )
        rem_res = await session.execute(
            select(ProductIngredient.position)
            .where(ProductIngredient.product_id == pid)
            .order_by(ProductIngredient.position.asc())
        )
        remaining_positions = rem_res.scalars().all()

        # Pass 1: offset by +1000 to prevent unique key collisions
        await session.execute(
            update(ProductIngredient)
            .where(ProductIngredient.product_id == pid)
            .values(position=ProductIngredient.position + 1000)
        )

        # Pass 2: assign contiguous 1..N
        for new_pos, old_pos in enumerate(remaining_positions, start=1):
            await session.execute(
                update(ProductIngredient)
                .where(
                    ProductIngredient.product_id == pid,
                    ProductIngredient.position == old_pos + 1000,
                )
                .values(position=new_pos)
            )

        await session.execute(update(Product).where(Product.id == pid).values(score_dirty=True))

    # Garbage Ingredient rows
    ing_res = await session.execute(select(Ingredient.id, Ingredient.inci_name))
    all_ings = ing_res.all()
    invalid_ing_ids = [ing_id for ing_id, inci in all_ings if not is_valid_ingredient_token(inci)]

    total_purged_ing = len(invalid_ing_ids)
    if invalid_ing_ids:
        pi_ref_res = await session.execute(
            select(ProductIngredient.product_id).where(
                ProductIngredient.ingredient_id.in_(invalid_ing_ids)
            )
        )
        affected_pids = set(pi_ref_res.scalars().all())
        if affected_pids:
            await session.execute(
                delete(ProductIngredient).where(
                    ProductIngredient.ingredient_id.in_(invalid_ing_ids)
                )
            )
            for pid in affected_pids:
                rem_res = await session.execute(
                    select(ProductIngredient.position)
                    .where(ProductIngredient.product_id == pid)
                    .order_by(ProductIngredient.position.asc())
                )
                rem_positions = rem_res.scalars().all()
                await session.execute(
                    update(ProductIngredient)
                    .where(ProductIngredient.product_id == pid)
                    .values(position=ProductIngredient.position + 1000)
                )
                for new_pos, old_pos in enumerate(rem_positions, start=1):
                    await session.execute(
                        update(ProductIngredient)
                        .where(
                            ProductIngredient.product_id == pid,
                            ProductIngredient.position == old_pos + 1000,
                        )
                        .values(position=new_pos)
                    )
                await session.execute(
                    update(Product).where(Product.id == pid).values(score_dirty=True)
                )

        await session.execute(delete(Ingredient).where(Ingredient.id.in_(invalid_ing_ids)))

    await session.commit()
    logger.info(
        "Step 2 complete: Purged %d invalid product_ingredients, %d invalid ingredients.",
        total_purged_pi,
        total_purged_ing,
    )
    return total_purged_pi, total_purged_ing


async def step3_quarantine_insufficient_ingredients(session: AsyncSession) -> int:
    """Step 3: Quarantine and delete products with < 2 ingredients."""
    logger.info("--- Step 3: Quarantining products with < 2 ingredients ---")
    ingestion_svc = IngestionService(session)

    stmt = (
        select(Product)
        .outerjoin(ProductIngredient, Product.id == ProductIngredient.product_id)
        .group_by(Product.id)
        .having(func.count(ProductIngredient.product_id) < 2)
    )
    res = await session.execute(stmt)
    products_to_quarantine = res.scalars().all()

    count = 0
    for p in products_to_quarantine:
        await ingestion_svc.quarantine(
            raw_product_id=None,
            stage="post_audit",
            reason="insufficient_valid_ingredients",
            payload={
                "barcode": p.barcode,
                "name": p.name,
                "raw_ingredients_text": p.raw_ingredients_text,
                "source": p.source.value,
            },
        )
        await session.delete(p)
        count += 1

    await session.commit()
    logger.info("Step 3 complete: Quarantined and deleted %d products.", count)
    return count


async def step4_clean_and_merge_brands(session: AsyncSession) -> tuple[int, int]:
    """Step 4: Clean and merge 'xx:' brand prefixes matching ^[a-zA-Z]{2}:."""
    logger.info("--- Step 4: Cleaning and merging prefixed brands ---")
    stmt = select(Brand).where(Brand.name.op("~")(r"^[a-zA-Z]{2}:\s*"))
    res = await session.execute(stmt)
    prefixed_brands = res.scalars().all()

    merged_count = 0
    renamed_count = 0

    for b in prefixed_brands:
        clean_name = _clean_brand_token(b.name, from_tags=True)
        if not clean_name or clean_name == b.name:
            continue

        existing_res = await session.execute(
            select(Brand).where(
                func.lower(Brand.name) == func.lower(clean_name),
                Brand.id != b.id,
            )
        )
        target_brand = existing_res.scalar_one_or_none()

        if target_brand is not None:
            await session.execute(
                update(Product).where(Product.brand_id == b.id).values(brand_id=target_brand.id)
            )
            await session.delete(b)
            merged_count += 1
        else:
            b.name = clean_name
            await session.flush()
            renamed_count += 1

    await session.commit()
    logger.info(
        "Step 4 complete: Renamed %d brands, merged %d brands.",
        renamed_count,
        merged_count,
    )
    return renamed_count, merged_count


async def step5_repair_corrupted_translations(session: AsyncSession) -> int:
    """Step 5: Repair corrupted ingredient translations."""
    logger.info("--- Step 5: Repairing corrupted translations ---")
    stmt = (
        select(IngredientTranslation, Ingredient)
        .join(Ingredient, IngredientTranslation.ingredient_id == Ingredient.id)
        .where(
            or_(
                func.strpos(IngredientTranslation.rationale, chr(65533)) > 0,
                IngredientTranslation.rationale.op("~")(r"[a-zA-ZÀ-ÿ]\?[a-zA-ZÀ-ÿ]"),
                func.strpos(func.coalesce(IngredientTranslation.summary, ""), chr(65533)) > 0,
            )
        )
    )
    res = await session.execute(stmt)
    rows = res.all()

    count = 0
    for trans, ing in rows:
        locale = trans.locale
        functions = ing.functions or ()
        if locale == "fr":
            summary = (
                f"Ingrédient cosmétique ayant pour fonction : {', '.join(functions)}."
                if functions
                else f"Ingrédient de formulation cosmétique ({ing.inci_name})."
            )
            if ing.is_prohibited:
                concern = "Substance interdite selon l'Annexe II du règlement cosmétique européen."
            elif ing.is_restricted:
                concern = "Substance soumise à des restrictions selon l'Annexe III européenne."
            elif ing.is_allergen:
                concern = "Allergène parfumant soumis à déclaration obligatoire."
            else:
                concern = (
                    "Ingrédient cosmétique généralement bien toléré aux concentrations usuelles."
                )
            has_flag = ing.is_prohibited or ing.is_restricted or ing.is_allergen
            rationale = (
                f"Évaluation vérifiée selon {ing.source_ref}."
                if ing.source_ref
                else (concern if has_flag else summary)
            )
        else:
            summary = (
                f"Cosmetic ingredient functioning as {', '.join(functions)}."
                if functions
                else f"Standard cosmetic formulation ingredient ({ing.inci_name})."
            )
            if ing.is_prohibited:
                concern = "Prohibited substance under EU Cosmetic Regulation Annex II."
            elif ing.is_restricted:
                concern = "Restricted substance subject to concentration limits under EU Annex III."
            elif ing.is_allergen:
                concern = "Recognized fragrance allergen requiring label declaration."
            else:
                concern = (
                    "Generally well-tolerated cosmetic ingredient at standard formulation levels."
                )
            has_flag = ing.is_prohibited or ing.is_restricted or ing.is_allergen
            rationale = (
                f"Curated rating based on {ing.source_ref}."
                if ing.source_ref
                else (concern if has_flag else summary)
            )

        trans.summary = summary
        trans.concern_note = concern
        trans.rationale = rationale
        count += 1

    await session.commit()
    logger.info("Step 5 complete: Repaired %d corrupted translations.", count)
    return count


async def step6_reprocess_images(
    session: AsyncSession,
    settings: Settings,
    image_batch_limit: int = 200,
) -> tuple[int, int]:
    """Step 6: Re-treat products with missing or unprocessed images."""
    logger.info("--- Step 6: Re-processing products with candidate or missing images ---")
    ingestion_svc = IngestionService(session)

    cdn_base = settings.image_cdn_base_url
    stmt = (
        select(Product)
        .where(
            Product.image_status != ImageStatus.PROCESSED,
            or_(
                Product.image_source_url.is_not(None),
                and_(
                    Product.image_url.is_not(None),
                    not_(Product.image_url.startswith(cdn_base)),
                ),
            ),
        )
        .limit(image_batch_limit)
    )
    res = await session.execute(stmt)
    products_needing_image = res.scalars().all()

    enqueued_images = 0
    for p in products_needing_image:
        p.image_source_url = p.image_source_url or p.image_url
        p.image_status = ImageStatus.CANDIDATE
        await enqueue_job(
            session,
            queue="enrichment",
            task_name="process_product_image",
            payload={"product_id": str(p.id)},
        )
        enqueued_images += 1

    # Scraped products with no image
    no_img_stmt = select(Product).where(
        Product.image_url.is_(None),
        Product.image_source_url.is_(None),
        Product.source == ProductSource.SCRAPE,
    )
    res_no_img = await session.execute(no_img_stmt)
    scraped_no_img = res_no_img.scalars().all()

    re_enriched = 0
    for p in scraped_no_img:
        raw = await session.scalar(
            select(RawProduct).where(RawProduct.source_id == p.source_id).limit(1)
        )
        if raw is not None:
            await enqueue_job(
                session,
                queue="enrichment",
                task_name="enrich_raw_product",
                payload={"raw_product_id": str(raw.id)},
            )
            re_enriched += 1
        else:
            await ingestion_svc.quarantine(
                raw_product_id=None,
                stage="image_pipeline",
                reason="missing_image",
                payload={"barcode": p.barcode, "product_id": str(p.id)},
            )

    await session.commit()
    logger.info(
        "Step 6 complete: Enqueued %d images, %d scraped products re-enqueued/quarantined.",
        enqueued_images,
        re_enriched,
    )
    return enqueued_images, re_enriched


async def step7_reset_jobs_rate_and_rescore(
    session: AsyncSession,
    rate_now: bool = False,
    rate_limit: int = 100,
    drain_worker: bool = False,
    max_jobs: int = 200,
) -> dict[str, int]:
    """Step 7: Reset failed jobs, rematch ingredients, rate unrated, and rescore products."""
    logger.info("--- Step 7: Rematching ingredients, rating, and rescoring ---")
    catalog_svc = CatalogService(session)
    ing_svc = IngredientService(session)

    del_res = await session.execute(
        delete(Job).where(
            Job.status == JobStatus.FAILED,
            Job.task_name.in_(["rate_ingredients", "process_product_image"]),
        )
    )
    deleted_failed_jobs = int(getattr(del_res, "rowcount", 0) or 0)
    await session.commit()

    total_rematched = 0
    while True:
        rematched = await catalog_svc.rematch_unmatched(batch_size=1000)
        total_rematched += rematched
        if rematched == 0:
            break
    logger.info("Rematched %d ingredients against dictionary.", total_rematched)

    rated_count = 0
    if rate_now:
        unrated_ids = await ing_svc.find_unrated_ingredient_ids(
            limit=rate_limit, only_product_linked=True
        )
        if unrated_ids:
            logger.info("Rating %d product-linked ingredients directly...", len(unrated_ids))
            enrichment_svc = EnrichmentService(session)
            rated_count = await enrichment_svc.rate_ingredients(unrated_ids)
            logger.info("Successfully rated %d ingredients.", rated_count)
    else:
        await enqueue_singleton_job(
            session,
            task_name="rate_ingredients",
            payload={"batch_size": rate_limit},
            queue="default",
        )
        logger.info("Enqueued rate_ingredients singleton job.")

    total_rescored = 0
    while True:
        rescored = await catalog_svc.recompute_dirty_scores(batch_size=500)
        total_rescored += rescored
        if rescored == 0:
            break
    logger.info("Rescored %d dirty products.", total_rescored)

    drained_jobs = 0
    if drain_worker:
        logger.info("Draining pending background jobs (max %d)...", max_jobs)
        for q in ["enrichment", "default"]:
            d = await run_pending_jobs(session, queue=q, limit=max_jobs)
            drained_jobs += d
            logger.info("Drained %d jobs from queue '%s'.", d, q)

    await session.commit()
    logger.info("Step 7 complete.")
    return {
        "deleted_failed_jobs": deleted_failed_jobs,
        "total_rematched": total_rematched,
        "rated_count": rated_count,
        "total_rescored": total_rescored,
        "drained_jobs": drained_jobs,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Idempotent, transactional retro-sanitizer for DermaScan."
    )
    parser.add_argument(
        "--image-batch-limit",
        type=int,
        default=200,
        help="Max images to enqueue in step 6 (default: 200).",
    )
    parser.add_argument(
        "--rate-now",
        action="store_true",
        default=False,
        help="Immediately rate unrated product-linked ingredients synchronously.",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=100,
        help="Max product-linked ingredients to rate (default: 100).",
    )
    parser.add_argument(
        "--drain-worker",
        action="store_true",
        default=False,
        help="Drain pending jobs in queues after sanitation.",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=200,
        help="Max jobs to drain when --drain-worker is set (default: 200).",
    )
    return parser.parse_args(argv)


async def main() -> int:
    args = parse_args()
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    logger.info("Starting Retro-Sanitizer execution...")
    async with session_factory() as session:
        await step1_seed_curated_ingredients(session)
        await step2_purge_garbage_tokens(session)
        await step3_quarantine_insufficient_ingredients(session)
        await step4_clean_and_merge_brands(session)
        await step5_repair_corrupted_translations(session)
        await step6_reprocess_images(
            session,
            settings=settings,
            image_batch_limit=args.image_batch_limit,
        )
        await step7_reset_jobs_rate_and_rescore(
            session,
            rate_now=args.rate_now,
            rate_limit=args.rate_limit,
            drain_worker=args.drain_worker,
            max_jobs=args.max_jobs,
        )

    await engine.dispose()
    logger.info("Retro-Sanitizer finished successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
