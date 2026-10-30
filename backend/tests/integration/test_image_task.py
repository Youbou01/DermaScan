import io
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, ProductUpsert
from app.modules.catalog.enums import EnrichmentStatus, ImageStatus, ProductSource
from app.modules.enrichment.tasks import process_product_image_task


def _create_sample_image(width: int = 600, height: int = 800) -> bytes:
    img = Image.new("RGB", (width, height), (255, 255, 255))
    for x in range(0, width, 50):
        for y in range(0, height, 50):
            img.putpixel((x, y), (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_process_product_image_task_success(db_session: AsyncSession) -> None:
    catalog = CatalogService(db_session)
    barcode = "7777777777777"
    dto = ProductUpsert(
        barcode=barcode,
        name="Sunscreen SPF 50",
        source=ProductSource.OPEN_BEAUTY_FACTS,
        source_id="img-test-1",
        image_source_url="http://example.com/images/sunscreen.jpg",
        enrichment_status=EnrichmentStatus.DONE,
    )
    product = await catalog.upsert_product(dto)
    assert product.image_status == ImageStatus.NONE or product.image_status == ImageStatus.CANDIDATE

    image_bytes = _create_sample_image(600, 800)

    # Mock HTTP response
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.content = image_bytes

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        await process_product_image_task({"product_id": str(product.id)}, db_session)

    # Refresh product
    info = await catalog.get_image_info(product.id)
    assert info is not None
    _, _, status = info
    assert status == ImageStatus.PROCESSED

    loaded = await catalog.get_product_detail(product.id, locale="en")
    assert loaded is not None
    assert loaded.image_url is not None
    assert f"products/{barcode}/" in loaded.image_url
    assert loaded.image_url.endswith(".webp")


@pytest.mark.asyncio
async def test_process_product_image_task_invalid_candidate(db_session: AsyncSession) -> None:
    catalog = CatalogService(db_session)
    barcode = "8888888888888"
    dto = ProductUpsert(
        barcode=barcode,
        name="Small Image Product",
        source=ProductSource.OPEN_BEAUTY_FACTS,
        source_id="img-test-2",
        image_source_url="http://example.com/images/tiny.jpg",
        enrichment_status=EnrichmentStatus.DONE,
    )
    product = await catalog.upsert_product(dto)

    # Tiny image 100x100
    tiny_bytes = _create_sample_image(100, 100)
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.content = tiny_bytes

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        await process_product_image_task({"product_id": str(product.id)}, db_session)

    info = await catalog.get_image_info(product.id)
    assert info is not None
    _, _, status = info
    assert status == ImageStatus.NONE

    loaded = await catalog.get_product_detail(product.id, locale="en")
    assert loaded is not None
    assert loaded.image_url is None
