import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import BarcodeMiss
from tests.factories import make_barcode

pytestmark = pytest.mark.usefixtures("migrated_database")

PRODUCTS = "/api/v1/products"


async def miss_count(session: AsyncSession, barcode: str) -> int | None:
    return await session.scalar(select(BarcodeMiss.count).where(BarcodeMiss.barcode == barcode))


async def test_unknown_barcode_is_a_404_and_is_counted(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    barcode = make_barcode()

    first = await client.get(f"{PRODUCTS}/by-barcode/{barcode}")
    assert first.status_code == 404
    assert await miss_count(db_session, barcode) == 1

    second = await client.get(f"{PRODUCTS}/by-barcode/{barcode}")
    assert second.status_code == 404
    assert await miss_count(db_session, barcode) == 2


async def test_malformed_barcode_is_a_422_and_is_not_counted(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    response = await client.get(f"{PRODUCTS}/by-barcode/1234567890123")

    assert response.status_code == 422
    total = await db_session.scalar(select(func.count()).select_from(BarcodeMiss))
    assert total == 0
