from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_session
from app.core.jobs import Job
from app.main import create_app
from app.modules.ingestion import IngestionService, RawProductSource
from app.modules.ingestion.models import RawProduct, ScrapeStaging
from app.modules.ingestion.tasks import scrape_url_task

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "html"


@pytest.fixture
def admin_settings() -> Settings:
    return Settings(
        admin_api_key="super-secret-admin-key",
        admin_ui_user="admin",
        admin_ui_password="password",  # noqa: S106
        app_env="test",
    )


@pytest.mark.asyncio
async def test_admin_ingestion_urls(admin_settings: Settings, db_session: AsyncSession) -> None:
    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        headers = {"X-Admin-Key": "super-secret-admin-key"}
        urls = [
            "https://example.com/product/1",
            "https://example.com/product/2",
        ]
        res = await client.post(
            "/admin/ingestion/urls",
            headers=headers,
            json={"urls": urls, "site_config": "default"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["enqueued"] == 2
        assert "run_id" in data

        # Verify jobs enqueued in DB
        stmt = select(Job).where(Job.task_name == "scrape_url")
        jobs = (await db_session.execute(stmt)).scalars().all()
        assert len(jobs) >= 2


@pytest.mark.asyncio
async def test_admin_ingestion_sitemap(admin_settings: Settings, db_session: AsyncSession) -> None:
    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session

    sitemap_xml = (FIXTURES_DIR / "sample_sitemap.xml").read_text(encoding="utf-8")

    # Mock httpx response for sitemap
    mock_resp = httpx.Response(
        status_code=200,
        text=sitemap_xml,
        request=httpx.Request("GET", "https://example.com/sitemap.xml"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            headers = {"X-Admin-Key": "super-secret-admin-key"}
            res = await client.post(
                "/admin/ingestion/sitemap",
                headers=headers,
                json={
                    "sitemap_url": "https://example.com/sitemap.xml",
                    "url_pattern": "/produit/",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["found_urls"] == 2
            assert data["enqueued"] == 2


@pytest.mark.asyncio
async def test_admin_ingestion_obf_run(admin_settings: Settings, db_session: AsyncSession) -> None:
    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        headers = {"X-Admin-Key": "super-secret-admin-key"}
        res = await client.post(
            "/admin/ingestion/obf/run",
            headers=headers,
            json={"barcodes": ["3017620422003", "3600523823123"]},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 2
        assert data["status"] == "started"


@pytest.mark.asyncio
async def test_scrape_url_task_execution(db_session: AsyncSession) -> None:
    ingestion = IngestionService(db_session)
    run = await ingestion.create_run(source="scrape")
    await db_session.commit()

    sample_extracted = {
        "url": "https://example.com/product/test-cream",
        "barcode": "3600523823123",
        "name": "Test Hydrating Cream",
        "brand_name": "DermaLab",
        "category_slug": "moisturizer",
        "raw_ingredients_text": "Aqua, Glycerin, Dimethicone",
        "image_url": "https://example.com/img.jpg",
        "source_lang": "en",
    }

    with patch(
        "app.modules.ingestion.sources.scraper.GenericScraperAdapter.fetch",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = sample_extracted

        await scrape_url_task(
            {
                "url": "https://example.com/product/test-cream",
                "site_config": "default",
                "run_id": str(run.id),
            },
            db_session,
        )
        await db_session.commit()

        # 1. Verify scrape_staging record
        stmt_stage = select(ScrapeStaging).where(
            ScrapeStaging.url == "https://example.com/product/test-cream"
        )
        stage_item = (await db_session.execute(stmt_stage)).scalar_one_or_none()
        assert stage_item is not None
        assert stage_item.status == "extracted"

        # 2. Verify raw_product record
        stmt_raw = select(RawProduct).where(
            RawProduct.source == RawProductSource.SCRAPE,
            RawProduct.source_id == "3600523823123",
        )
        raw_prod = (await db_session.execute(stmt_raw)).scalar_one_or_none()
        assert raw_prod is not None
        assert raw_prod.payload["name"] == "Test Hydrating Cream"

        # 3. Verify enrich_raw_product job enqueued
        stmt_job = select(Job).where(
            Job.task_name == "enrich_raw_product",
            Job.payload["raw_product_id"].as_string() == str(raw_prod.id),
        )
        job = (await db_session.execute(stmt_job)).scalar_one_or_none()
        assert job is not None
