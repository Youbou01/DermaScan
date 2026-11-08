import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, ProductUpsert
from app.modules.catalog.enums import EnrichmentStatus, ProductSource
from app.modules.catalog.gtin import compute_check_digit
from app.modules.ingestion import RawProductSource, RawRecord, store_raw_product
from app.modules.ingestion.models import QuarantineItem
from app.modules.ingestion.tasks import enrich_raw_product_task


def make_valid_barcode() -> str:
    body = f"333{uuid.uuid4().int % 1000000000:09d}"
    return body + str(compute_check_digit(body))


@pytest.mark.asyncio
async def test_canonical_barcode_deduplication(db_session: AsyncSession) -> None:
    catalog = CatalogService(db_session)
    barcode = make_valid_barcode()

    # 1. Upsert initial product
    p1 = await catalog.upsert_product(
        ProductUpsert(
            barcode=barcode,
            name="CeraVe Moisturizing Cream",
            source=ProductSource.OPEN_BEAUTY_FACTS,
            source_id=f"obf-{barcode}",
            brand_name="CeraVe",
        )
    )
    await db_session.commit()

    # 2. Check canonical matching with same barcode but different title/source
    res = await catalog.resolve_or_deduplicate(
        barcode=barcode,
        name="Moisturizing Cream by CeraVe",
        brand_name="CeraVe",
        source=ProductSource.SCRAPE,
        source_id="scrape-123",
    )
    assert res.match_status == "exact_barcode"
    assert res.product_id == p1.id


@pytest.mark.asyncio
async def test_high_confidence_fuzzy_deduplication(db_session: AsyncSession) -> None:
    catalog = CatalogService(db_session)
    barcode = make_valid_barcode()

    p1 = await catalog.upsert_product(
        ProductUpsert(
            barcode=barcode,
            name="Hydrating Facial Cleanser 236ml",
            source=ProductSource.OPEN_BEAUTY_FACTS,
            source_id=f"obf-{barcode}",
            brand_name="CeraVe",
        )
    )
    await db_session.commit()

    # Barcodeless candidate with very high similarity (normalized: hydrating facial cleanser)
    res = await catalog.resolve_or_deduplicate(
        barcode=None,
        name="Hydrating Facial Cleanser",
        brand_name="CeraVe",
        source=ProductSource.SCRAPE,
        source_id="scrape-no-barcode",
    )
    assert res.match_status == "fuzzy_match"
    assert res.product_id == p1.id
    assert res.similarity is not None
    assert res.similarity >= 0.80


@pytest.mark.asyncio
async def test_ambiguous_fuzzy_match_quarantine(db_session: AsyncSession) -> None:
    catalog = CatalogService(db_session)
    barcode1 = make_valid_barcode()

    # Seed existing product
    p1 = await catalog.upsert_product(
        ProductUpsert(
            barcode=barcode1,
            name="Toleriane Dermallergo Soothing Cream",
            source=ProductSource.OPEN_BEAUTY_FACTS,
            source_id=f"obf-{barcode1}",
            brand_name="La Roche-Posay",
        )
    )
    await db_session.commit()

    # Test ambiguous match: sharing brand and series but different sub-product
    res = await catalog.resolve_or_deduplicate(
        barcode=None,
        name="Toleriane Dermallergo Soothing Fluid",
        brand_name="La Roche-Posay",
    )
    assert res.match_status == "ambiguous"
    assert res.product_id == p1.id
    assert res.similarity is not None
    assert 0.50 <= res.similarity < 0.80

    # Run through enrichment pipeline and verify quarantine routing
    raw_payload = {
        "barcode": None,
        "name": "Toleriane Dermallergo Soothing Fluid",
        "brand_name": "La Roche-Posay",
        "raw_ingredients_text": "Aqua, Glycerin, Squalane",
    }
    raw_rec = RawRecord(
        source=RawProductSource.SCRAPE.value,
        source_id=f"scrape-ambig-{uuid.uuid4().hex[:6]}",
        content_hash=f"ambig-hash-{uuid.uuid4().hex[:8]}",
        payload=raw_payload,
    )
    raw_id = await store_raw_product(db_session, raw_rec)
    await db_session.commit()
    assert raw_id is not None

    from unittest.mock import AsyncMock, patch

    from app.modules.enrichment.schemas import (
        EnrichmentOutcome,
        IngredientInciItem,
        ProductEnrichmentResult,
    )

    enrich_res = EnrichmentOutcome(
        status=EnrichmentStatus.DONE,
        result=ProductEnrichmentResult(
            is_skincare=True,
            is_skincare_confidence=1.0,
            brand="La Roche-Posay",
            name_clean="Toleriane Dermallergo Soothing Fluid",
            ingredients_inci=[
                IngredientInciItem(original="Aqua", inci="Aqua"),
                IngredientInciItem(original="Glycerin", inci="Glycerin"),
                IngredientInciItem(original="Squalane", inci="Squalane"),
            ],
        ),
    )

    with patch(
        "app.modules.enrichment.EnrichmentService.enrich_product",
        new_callable=AsyncMock,
    ) as mock_enrich:
        mock_enrich.return_value = enrich_res
        await enrich_raw_product_task({"raw_product_id": str(raw_id)}, db_session)
        await db_session.commit()

    # Verify quarantined with reason 'ambiguous_duplicate'
    stmt_q = select(QuarantineItem).where(
        QuarantineItem.raw_product_id == raw_id,
        QuarantineItem.stage == "deduplication",
    )
    q_item = (await db_session.execute(stmt_q)).scalar_one_or_none()
    assert q_item is not None
    assert q_item.reason == "ambiguous_duplicate"
    assert q_item.payload["matched_product_id"] == str(p1.id)


@pytest.mark.asyncio
async def test_distinct_product_is_new(db_session: AsyncSession) -> None:
    catalog = CatalogService(db_session)
    barcode = make_valid_barcode()

    await catalog.upsert_product(
        ProductUpsert(
            barcode=barcode,
            name="Cleanance Comedomed Anti-Blemish Concentrate",
            source=ProductSource.OPEN_BEAUTY_FACTS,
            source_id=f"obf-{barcode}",
            brand_name="Avène",
        )
    )
    await db_session.commit()

    res = await catalog.resolve_or_deduplicate(
        barcode=None,
        name="Nutritive Lip Balm",
        brand_name="Bioderma",
    )
    assert res.match_status == "new"
    assert res.product_id is None
