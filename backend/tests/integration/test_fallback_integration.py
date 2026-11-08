"""Integration tests for OBF async fallback with recorded HTTP fixtures."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import BarcodeMiss, Product
from app.modules.ingestion.fallback import handle_barcode_miss_fallback
from app.modules.ingestion.seed_categories import seed_categories
from tests.factories import make_barcode

pytestmark = pytest.mark.usefixtures("migrated_database")


async def test_fallback_imports_product_on_200(db_session: AsyncSession) -> None:
    await seed_categories(db_session, commit=False)
    barcode = make_barcode()
    sample_obf_payload = {
        "status": 1,
        "product": {
            "code": barcode,
            "product_name": "Hydrating Facial Cream",
            "ingredients_text": "Aqua, Glycerin, Niacinamide, Tocopherol",
            "brands": "CeraVe",
            "categories_tags": ["en:face-creams"],
            "image_url": "https://images.openbeautyfacts.org/front.jpg",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=sample_obf_payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        detail = await handle_barcode_miss_fallback(db_session, barcode, locale="en", client=client)
        assert detail is not None
        assert detail.barcode == barcode
        assert detail.name == "Hydrating Facial Cream"
        assert detail.category is not None
        assert detail.category.slug == "moisturizer"

        # Verify product is persisted in DB
        prod = await db_session.scalar(select(Product).where(Product.barcode == barcode))
        assert prod is not None
        assert prod.name_normalized == "hydrating facial cream"


async def test_fallback_handles_404_and_negative_cache(db_session: AsyncSession) -> None:
    barcode = make_barcode()
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(404, json={"status": 0, "status_verbose": "product not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        # First call: makes HTTP request, returns None
        detail1 = await handle_barcode_miss_fallback(
            db_session, barcode, locale="en", client=client
        )
        assert detail1 is None
        assert call_count == 1

        miss = await db_session.scalar(select(BarcodeMiss).where(BarcodeMiss.barcode == barcode))
        assert miss is not None
        assert miss.count == 1

        # Second call: negative cache hit (<24h), no HTTP request made!
        detail2 = await handle_barcode_miss_fallback(
            db_session, barcode, locale="en", client=client
        )
        assert detail2 is None
        assert call_count == 1  # Still 1!


async def test_fallback_handles_timeout_gracefully(db_session: AsyncSession) -> None:
    barcode = make_barcode()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("OBF API timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        detail = await handle_barcode_miss_fallback(db_session, barcode, locale="en", client=client)
        assert detail is None
        miss = await db_session.scalar(select(BarcodeMiss).where(BarcodeMiss.barcode == barcode))
        assert miss is not None
