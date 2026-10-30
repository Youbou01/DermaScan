import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_session
from app.main import create_app
from app.modules.catalog import CatalogService, ProductUpsert
from app.modules.catalog.enums import EnrichmentStatus, ProductSource
from app.modules.ingestion import IngestionService, QuarantineStatus
from app.modules.ingredients import IngredientService


@pytest.fixture
def admin_settings() -> Settings:
    return Settings(
        admin_api_key="super-secret-admin-key",
        admin_ui_user="admin",
        admin_ui_password="password",  # noqa: S106
        app_env="test",
    )


@pytest.mark.asyncio
async def test_admin_api_auth_required(admin_settings: Settings, db_session: AsyncSession) -> None:
    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Missing header
        res_no_key = await client.get("/admin/review/quarantine")
        assert res_no_key.status_code == 401

        # Invalid key
        res_bad_key = await client.get(
            "/admin/review/quarantine", headers={"X-Admin-Key": "wrong-key"}
        )
        assert res_bad_key.status_code == 401


@pytest.mark.asyncio
async def test_admin_quarantine_review_flow(
    admin_settings: Settings, db_session: AsyncSession
) -> None:
    ingestion = IngestionService(db_session)
    q_item = await ingestion.quarantine(
        raw_product_id=None,
        stage="enrichment",
        reason="test_quarantine_reason",
        payload={"sample": "data"},
    )
    await db_session.commit()

    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        headers = {"X-Admin-Key": "super-secret-admin-key"}

        # 1. List quarantine
        res_list = await client.get("/admin/review/quarantine", headers=headers)
        assert res_list.status_code == 200
        items = res_list.json()
        assert any(i["id"] == str(q_item.id) for i in items)

        # 2. Approve
        res_approve = await client.post(f"/admin/review/{q_item.id}/approve", headers=headers)
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "approved"

        # Verify DB status updated
        item_db = await ingestion.get_quarantine_item(q_item.id)
        assert item_db is not None
        assert item_db.status == QuarantineStatus.APPROVED

        # 3. Reject
        res_reject = await client.post(f"/admin/review/{q_item.id}/reject", headers=headers)
        assert res_reject.status_code == 200
        assert res_reject.json()["status"] == "rejected"

        item_db2 = await ingestion.get_quarantine_item(q_item.id)
        assert item_db2 is not None
        assert item_db2.status == QuarantineStatus.REJECTED


@pytest.mark.asyncio
async def test_admin_curated_rating_lock_and_dirty(
    admin_settings: Settings, db_session: AsyncSession
) -> None:
    # Seed an ingredient
    from app.modules.ingredients.models import Ingredient

    ing = Ingredient(
        inci_name=f"ADMIN_TEST_ING_{uuid.uuid4().hex[:8]}",
        rating=None,
        risk_level="unknown",
        rating_source="unrated",
        rating_version=1,
    )
    db_session.add(ing)
    await db_session.flush()

    # Create product using this ingredient
    catalog = CatalogService(db_session)
    barcode = f"999{uuid.uuid4().int % 10000000000:010d}"
    dto = ProductUpsert(
        barcode=barcode,
        name="Admin Test Product",
        source=ProductSource.OPEN_BEAUTY_FACTS,
        source_id=f"src-{barcode}",
        ingredients=[(1, "raw_ing", ing.id)],
        enrichment_status=EnrichmentStatus.DONE,
    )
    product = await catalog.upsert_product(dto)
    await db_session.commit()

    prod_fresh = await catalog.get_product_detail(product.id, locale="en")
    assert prod_fresh.id == product.id

    # Update rating via admin API
    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        headers = {"X-Admin-Key": "super-secret-admin-key"}
        res = await client.post(
            f"/admin/ingredients/{ing.id}/rating",
            headers=headers,
            json={
                "rating": 9.5,
                "summary": "Excellent gentle soothing agent",
                "concern_note": None,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["rating"] == 9.5
        assert data["rating_source"] == "curated"
        assert data["affected_products"] >= 1

    # Verify ingredient locked as curated in database
    ing_service = IngredientService(db_session)
    updated_info = (await ing_service.get_many([ing.id], locale="en"))[ing.id]
    assert updated_info.rating is not None
    assert float(updated_info.rating) == 9.5
    assert updated_info.risk_level.value == "low"
    assert updated_info.summary == "Excellent gentle soothing agent"


@pytest.mark.asyncio
async def test_admin_ingestion_runs(admin_settings: Settings, db_session: AsyncSession) -> None:
    from app.modules.ingestion.models import IngestionRun

    run = IngestionRun(
        source="open_beauty_facts",
        counters={"products_fetched": 10, "products_imported": 8, "error_count": 2},
    )
    db_session.add(run)
    await db_session.commit()

    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        headers = {"X-Admin-Key": "super-secret-admin-key"}
        res = await client.get("/admin/ingestion/runs", headers=headers)
        assert res.status_code == 200
        runs = res.json()
        assert len(runs) >= 1
        assert any(r["id"] == str(run.id) for r in runs)


@pytest.mark.asyncio
async def test_admin_ui_auth(
    admin_settings: Settings, db_session: AsyncSession, migrated_database: str
) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.api.admin.app import init_admin_ui

    app = create_app(admin_settings)
    app.dependency_overrides[get_session] = lambda: db_session
    admin_app = app.state.admin_app
    engine = create_async_engine(migrated_database)
    init_admin_ui(admin_app, engine, admin_settings)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # Unauthenticated request to /admin/ui/ should redirect to /admin/ui/login
            res = await client.get("/admin/ui/", follow_redirects=False)
            assert res.status_code in (302, 303, 307)
            assert "/admin/ui/login" in res.headers.get("location", "")

            # GET login page
            res_login_page = await client.get("/admin/ui/login")
            assert res_login_page.status_code == 200

            # Login with correct credentials
            res_post = await client.post(
                "/admin/ui/login",
                data={"username": "admin", "password": "password"},
                follow_redirects=False,
            )
            assert res_post.status_code in (302, 303)
    finally:
        await engine.dispose()
