import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.models import RawProduct
from app.modules.ingestion.sources.base import RawRecord
from app.modules.ingestion.sources.obf import store_raw_product


@pytest.mark.asyncio
async def test_store_raw_product_idempotency(db_session: AsyncSession) -> None:
    record = RawRecord(
        source="open_beauty_facts",
        source_id="3017620422003",
        content_hash="abc1234567890123456789012345678901234567890123456789012345678901",
        payload={"code": "3017620422003", "brand": "Nutella Skincare"},
        url="https://world.openbeautyfacts.org/product/3017620422003",
    )

    # 1. First insert succeeds
    raw_id_1 = await store_raw_product(db_session, record)
    assert raw_id_1 is not None

    # Verify stored in DB
    stmt = select(RawProduct).where(RawProduct.id == raw_id_1)
    stored = (await db_session.execute(stmt)).scalar_one_or_none()
    assert stored is not None
    assert stored.source_id == "3017620422003"
    assert stored.payload["brand"] == "Nutella Skincare"

    # 2. Second insert with identical hash is skipped idempotently
    raw_id_2 = await store_raw_product(db_session, record)
    assert raw_id_2 is None

    # 3. Third insert with different hash (updated content) succeeds
    record_updated = RawRecord(
        source="open_beauty_facts",
        source_id="3017620422003",
        content_hash="def9999999999999999999999999999999999999999999999999999999999999",
        payload={"code": "3017620422003", "brand": "Nutella Skincare V2"},
        url="https://world.openbeautyfacts.org/product/3017620422003",
    )
    raw_id_3 = await store_raw_product(db_session, record_updated)
    assert raw_id_3 is not None
    assert raw_id_3 != raw_id_1
