"""End to end: refresh with the fixture source, then read through the offers endpoint."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.identity.models import UserAccount
from app.modules.offers.refresh import refresh_product_offers
from app.modules.offers.sources import (
    FIXTURE_NO_OFFERS,
    FIXTURE_NORMAL,
    FIXTURE_STALE,
    FixtureAdapter,
)
from tests.factories import make_product
from tests.offers_client import offers_http_client

pytestmark = pytest.mark.usefixtures("migrated_database")


@pytest.fixture
async def client(
    migrated_database: str, db_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    """The shared `client`, plus the offers router (registered by Dev 4 later)."""
    async with offers_http_client(migrated_database, db_session) as http_client:
        yield http_client


async def _auth_headers(session: AsyncSession) -> dict[str, str]:
    user = UserAccount(
        email=f"refresh-{uuid.uuid4().hex[:8]}@example.test",
        password_hash=hash_password("test-password"),
        display_name="Refresh user",
    )
    session.add(user)
    await session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _refreshed_offers(
    client: httpx.AsyncClient, session: AsyncSession, barcode: str
) -> dict[str, object]:
    product = make_product(barcode=barcode)
    session.add(product)
    await session.flush()
    await refresh_product_offers(
        session,
        product_id=product.id,
        barcode=product.barcode,
        product_name=product.name,
        adapter=FixtureAdapter(),
        source="fixture",
        now=datetime.now(UTC),
    )
    response = await client.get(
        f"/api/v1/products/{product.id}/offers", headers=await _auth_headers(session)
    )
    assert response.status_code == 200
    body: dict[str, object] = response.json()
    return body


async def test_normal_product_marks_the_cheapest_offer(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    body = await _refreshed_offers(client, db_session, FIXTURE_NORMAL)

    offers = {offer["price"]: offer for offer in body["offers"]}  # type: ignore[attr-defined]
    assert offers["12.00"]["is_cheapest"] is True
    assert offers["15.50"]["is_cheapest"] is False
    assert body["cheapest_offer_id"] == offers["12.00"]["id"]
    assert body["mixed_currencies"] is False


async def test_stale_offer_is_never_cheapest(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    body = await _refreshed_offers(client, db_session, FIXTURE_STALE)

    offers = {offer["price"]: offer for offer in body["offers"]}  # type: ignore[attr-defined]
    assert offers["5.00"]["freshness"] == "stale"
    assert offers["5.00"]["is_cheapest"] is False
    assert offers["9.00"]["freshness"] == "fresh"
    assert offers["9.00"]["is_cheapest"] is True
    assert body["cheapest_offer_id"] == offers["9.00"]["id"]


async def test_product_without_offers_returns_an_empty_list(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    body = await _refreshed_offers(client, db_session, FIXTURE_NO_OFFERS)

    assert body["offers"] == []
    assert body["cheapest_offer_id"] is None
