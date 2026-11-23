"""Integration coverage for GET /api/v1/products/{product_id}/offers."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.catalog.models import Product
from app.modules.identity.models import UserAccount
from app.modules.offers.enums import StockState
from app.modules.offers.models import ProductOffer, Retailer
from tests.factories import make_product
from tests.offers_client import offers_http_client


@pytest.fixture
async def client(
    migrated_database: str, db_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    """The shared `client`, plus the offers router (registered by Dev 4 later)."""
    async with offers_http_client(migrated_database, db_session) as http_client:
        yield http_client


async def _auth_headers(session: AsyncSession) -> dict[str, str]:
    user = UserAccount(
        email=f"offers-{uuid.uuid4().hex[:8]}@example.test",
        password_hash=hash_password("test-password"),
        display_name="Offers user",
    )
    session.add(user)
    await session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _product(session: AsyncSession) -> Product:
    product = make_product()
    session.add(product)
    await session.flush()
    return product


async def _add_offer(
    session: AsyncSession,
    product: Product,
    name: str,
    price: str,
    *,
    currency: str = "EUR",
    stock: StockState = StockState.IN_STOCK,
    age_days: float = 0,
) -> ProductOffer:
    retailer = Retailer(name=name, domain=f"{uuid.uuid4().hex[:8]}.example")
    session.add(retailer)
    await session.flush()
    offer = ProductOffer(
        product_id=product.id,
        retailer_id=retailer.id,
        price=Decimal(price),
        currency=currency,
        url=f"https://{retailer.domain}/p/1",
        stock_state=stock,
        source="fixture",
        last_checked_at=datetime.now(UTC) - timedelta(days=age_days),
        content_hash="0" * 64,
    )
    session.add(offer)
    await session.flush()
    return offer


async def _get(
    client: httpx.AsyncClient, session: AsyncSession, product_id: uuid.UUID
) -> httpx.Response:
    return await client.get(
        f"/api/v1/products/{product_id}/offers", headers=await _auth_headers(session)
    )


async def test_requires_authentication(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    product = await _product(db_session)

    response = await client.get(f"/api/v1/products/{product.id}/offers")

    assert response.status_code == 401


async def test_unknown_product_is_404(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    response = await _get(client, db_session, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["type"].endswith("product-not-found")


async def test_invalid_product_id_is_422(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    response = await client.get(
        "/api/v1/products/not-a-uuid/offers", headers=await _auth_headers(db_session)
    )

    assert response.status_code == 422


async def test_product_without_offers_gives_an_empty_list(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await _product(db_session)

    response = await _get(client, db_session, product.id)

    assert response.status_code == 200
    assert response.json() == {
        "product_id": str(product.id),
        "cheapest_offer_id": None,
        "mixed_currencies": False,
        "offers": [],
    }


async def test_cheapest_offer_is_flagged_and_offers_are_ordered(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await _product(db_session)
    await _add_offer(db_session, product, "Shop A", "15.50")
    cheapest = await _add_offer(db_session, product, "Shop B", "12.00")
    await _add_offer(db_session, product, "Shop Old", "1.00", age_days=30)
    await _add_offer(db_session, product, "Shop Out", "2.00", stock=StockState.OUT_OF_STOCK)

    response = await _get(client, db_session, product.id)

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["cheapest_offer_id"] == str(cheapest.id)
    assert body["mixed_currencies"] is False
    names = [o["retailer"]["name"] for o in body["offers"]]
    assert names == ["Shop B", "Shop A", "Shop Old", "Shop Out"]
    assert [o["is_cheapest"] for o in body["offers"]] == [True, False, False, False]
    by_name = {o["retailer"]["name"]: o for o in body["offers"]}
    assert by_name["Shop Old"]["freshness"] == "stale"
    assert by_name["Shop Out"]["stock_state"] == "out_of_stock"


async def test_price_is_serialized_as_a_string(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await _product(db_session)
    await _add_offer(db_session, product, "Shop A", "15.50")

    body = (await _get(client, db_session, product.id)).json()

    assert body["offers"][0]["price"] == "15.50"
    assert body["offers"][0]["currency"] == "EUR"


async def test_mixed_currencies_means_no_cheapest(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await _product(db_session)
    await _add_offer(db_session, product, "Shop A", "10.00")
    await _add_offer(db_session, product, "Shop B", "8.00", currency="USD")

    body = (await _get(client, db_session, product.id)).json()

    assert body["mixed_currencies"] is True
    assert body["cheapest_offer_id"] is None
    assert not any(o["is_cheapest"] for o in body["offers"])
