"""Integration coverage for personal library and dermatologist guidance APIs."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_session
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.modules.catalog.models import Product
from app.modules.dermatologists import dermatologists_router
from app.modules.dermatologists.models import RecommendationProduct
from app.modules.identity.models import UserAccount
from app.modules.personal_library import personal_library_router
from tests.factories import make_product

pytestmark = pytest.mark.usefixtures("migrated_database")

DRY_RECOMMENDATION_ID = "0194f024-6c67-7e21-9e16-a774b0d60012"


@pytest.fixture
async def feature_client(
    migrated_database: str, db_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(_env_file=None, app_env="test", database_url=migrated_database)
    app: FastAPI = create_app(settings)
    app.include_router(personal_library_router, prefix="/api/v1/library")
    app.include_router(dermatologists_router, prefix="/api/v1/dermatologists")

    async def use_test_session() -> AsyncIterator[AsyncSession]:
        db_session.expunge_all()
        yield db_session

    app.dependency_overrides[get_session] = use_test_session
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _user_headers(session: AsyncSession, email: str) -> dict[str, str]:
    user = UserAccount(
        email=email,
        password_hash=hash_password("test-password"),
        display_name="Library test user",
    )
    session.add(user)
    await session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _product(session: AsyncSession, name: str = "Library product") -> Product:
    product = make_product(name=name)
    session.add(product)
    await session.flush()
    return product


async def test_saved_products_and_recent_views_are_idempotent_and_private(
    feature_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _user_headers(db_session, "library-user@example.test")
    product = await _product(db_session)
    saved_url = f"/api/v1/library/saved/{product.id}"
    viewed_url = f"/api/v1/library/recently-viewed/{product.id}"

    assert (await feature_client.put(saved_url, headers=headers)).status_code == 204
    assert (await feature_client.put(saved_url, headers=headers)).status_code == 204
    saved = await feature_client.get("/api/v1/library/saved", headers=headers)
    assert saved.status_code == 200
    assert [item["id"] for item in saved.json()["items"]] == [str(product.id)]

    assert (await feature_client.put(viewed_url, headers=headers)).status_code == 204
    assert (await feature_client.put(viewed_url, headers=headers)).status_code == 204
    recent = await feature_client.get("/api/v1/library/recently-viewed", headers=headers)
    assert recent.status_code == 200
    assert [item["id"] for item in recent.json()["items"]] == [str(product.id)]

    other_headers = await _user_headers(db_session, "other-library-user@example.test")
    other_saved = await feature_client.get("/api/v1/library/saved", headers=other_headers)
    other_recent = await feature_client.get(
        "/api/v1/library/recently-viewed", headers=other_headers
    )
    assert other_saved.json()["items"] == []
    assert other_recent.json()["items"] == []

    assert (await feature_client.delete(saved_url, headers=headers)).status_code == 204
    assert (await feature_client.delete(saved_url, headers=headers)).status_code == 204
    assert (await feature_client.get("/api/v1/library/saved", headers=headers)).json()[
        "items"
    ] == []


async def test_recent_views_are_bounded_to_twenty(
    feature_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _user_headers(db_session, "recent-limit@example.test")
    products = [await _product(db_session, f"Viewed {index}") for index in range(21)]

    for product in products:
        response = await feature_client.put(
            f"/api/v1/library/recently-viewed/{product.id}", headers=headers
        )
        assert response.status_code == 204

    response = await feature_client.get("/api/v1/library/recently-viewed", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["items"]) == 20
    assert str(products[0].id) not in {item["id"] for item in response.json()["items"]}


async def test_public_guidance_uses_generic_and_skin_specific_content_without_profile_data(
    feature_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    response = await feature_client.get("/api/v1/dermatologists/recommendations")

    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["title"] == "A simple daily routine"
    assert body["recommendations"][0]["dermatologist"] is None
    assert "diagnosis" in body["disclaimer"]
    assert "user_id" not in response.text
    assert "health_conditions" not in response.text

    headers = await _user_headers(db_session, "guidance-user@example.test")
    await feature_client.put(
        "/api/v1/profile",
        headers=headers,
        json={"skin_type": "dry", "health_conditions": ["eczema"]},
    )
    product = await _product(db_session, "Dry skin linked product")
    db_session.add(
        RecommendationProduct(
            recommendation_id=DRY_RECOMMENDATION_ID,
            product_id=product.id,
            position=1,
        )
    )
    await db_session.flush()

    personalized = await feature_client.get(
        "/api/v1/dermatologists/recommendations", headers=headers
    )
    assert personalized.status_code == 200
    personalized_body = personalized.json()
    [recommendation] = personalized_body["recommendations"]
    assert recommendation["title"] == "Care for dry skin gently"
    assert recommendation["dermatologist"]["is_verified"] is True
    assert recommendation["related_products"][0]["id"] == str(product.id)
    assert "health_conditions" not in personalized.text
    assert "user_id" not in personalized.text

    french = await feature_client.get(
        "/api/v1/dermatologists/recommendations?skin_type=dry",
        headers={"Accept-Language": "fr"},
    )
    assert french.status_code == 200
    assert french.json()["recommendations"][0]["title"] == (
        "Prenez soin des peaux sèches en douceur"
    )


async def test_library_endpoints_require_authentication(
    feature_client: httpx.AsyncClient,
) -> None:
    response = await feature_client.get("/api/v1/library/saved")

    assert response.status_code == 401
