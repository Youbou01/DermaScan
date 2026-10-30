import io
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_session
from app.core.jobs import Job
from app.main import create_app
from app.modules.enrichment.schemas import OcrIngredientsResult
from app.modules.ingestion import QuarantineStatus, RawProductSource
from app.modules.ingestion.models import QuarantineItem, RawProduct


def make_image_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color="white")
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_submit_contribution_success(db_session: AsyncSession) -> None:
    settings = Settings(app_env="test")
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session

    image_bytes = make_image_bytes()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        files = {"photo": ("label.jpg", image_bytes, "image/jpeg")}
        data = {"barcode": "3600523823123"}
        res = await client.post("/api/v1/contributions", data=data, files=files)

        assert res.status_code == 202
        body = res.json()
        assert body["status"] == "processing"
        assert body["barcode"] == "3600523823123"
        assert "id" in body

        # Verify raw_product created
        stmt = select(RawProduct).where(
            RawProduct.source == RawProductSource.USER_PHOTO,
            RawProduct.source_id == "3600523823123",
        )
        raw = (await db_session.execute(stmt)).scalar_one_or_none()
        assert raw is not None
        assert "Aqua" in raw.payload["raw_ingredients_text"]

        # Verify job enqueued
        stmt_job = select(Job).where(
            Job.task_name == "enrich_raw_product",
            Job.payload["raw_product_id"].as_string() == str(raw.id),
        )
        job = (await db_session.execute(stmt_job)).scalar_one_or_none()
        assert job is not None


@pytest.mark.asyncio
async def test_submit_contribution_low_confidence_quarantined(
    db_session: AsyncSession,
) -> None:
    settings = Settings(app_env="test")
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session

    image_bytes = make_image_bytes()
    low_conf_ocr = OcrIngredientsResult(
        ingredients_text="blurry illegible label",
        confidence=0.3,
        is_readable=False,
    )

    with patch(
        "app.modules.enrichment.EnrichmentService.ocr_ingredients",
        new_callable=AsyncMock,
    ) as mock_ocr:
        mock_ocr.return_value = low_conf_ocr

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            files = {"photo": ("label.jpg", image_bytes, "image/jpeg")}
            data = {"barcode": "3600523823123"}
            res = await client.post("/api/v1/contributions", data=data, files=files)

            assert res.status_code == 202
            body = res.json()
            assert body["status"] == "quarantined"

            # Verify quarantine row created
            stmt_q = select(QuarantineItem).where(
                QuarantineItem.stage == "user_photo_ocr",
                QuarantineItem.status == QuarantineStatus.PENDING,
            )
            q_item = (await db_session.execute(stmt_q)).scalar_one_or_none()
            assert q_item is not None
            assert q_item.reason == "user_photo_low_confidence"


@pytest.mark.asyncio
async def test_submit_contribution_invalid_inputs(db_session: AsyncSession) -> None:
    settings = Settings(app_env="test")
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Invalid barcode
        files = {"photo": ("label.jpg", make_image_bytes(), "image/jpeg")}
        res_bad_bc = await client.post(
            "/api/v1/contributions", data={"barcode": "not-valid-gtin"}, files=files
        )
        assert res_bad_bc.status_code == 422

        # Invalid media type
        files_bad_mime = {"photo": ("label.txt", b"some text", "text/plain")}
        res_bad_mime = await client.post(
            "/api/v1/contributions", data={"barcode": "3600523823123"}, files=files_bad_mime
        )
        assert res_bad_mime.status_code == 415
