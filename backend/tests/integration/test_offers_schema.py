"""The offers schema must reject bad data by itself, not only the Python code."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Product
from app.modules.offers.enums import StockState
from app.modules.offers.models import ProductOffer, Retailer
from tests.factories import make_product

pytestmark = pytest.mark.usefixtures("migrated_database")


async def _product_and_retailer(session: AsyncSession) -> tuple[Product, Retailer]:
    product = make_product()
    retailer = Retailer(name="Shop A", domain=f"shop-{uuid.uuid4().hex[:8]}.example")
    session.add_all([product, retailer])
    await session.flush()
    return product, retailer


def _offer(product: Product, retailer: Retailer, **overrides: Any) -> ProductOffer:
    values: dict[str, Any] = {
        "product_id": product.id,
        "retailer_id": retailer.id,
        "price": Decimal("15.50"),
        "currency": "EUR",
        "url": "https://shop-a.example/p/1",
        "stock_state": StockState.IN_STOCK,
        "source": "fixture",
        "last_checked_at": datetime.now(UTC),
        "content_hash": "0" * 64,
    }
    values.update(overrides)
    return ProductOffer(**values)


async def test_defaults_are_filled_in(db_session: AsyncSession) -> None:
    product, retailer = await _product_and_retailer(db_session)
    offer = _offer(product, retailer)
    db_session.add(offer)
    await db_session.flush()
    await db_session.refresh(retailer)
    await db_session.refresh(offer)

    assert retailer.id.version == 7
    assert retailer.is_affiliate is False
    assert retailer.created_at is not None
    assert offer.created_at is not None
    assert offer.price == Decimal("15.50")


async def test_negative_price_is_rejected(db_session: AsyncSession) -> None:
    product, retailer = await _product_and_retailer(db_session)
    db_session.add(_offer(product, retailer, price=Decimal("-0.01")))

    with pytest.raises(IntegrityError, match="price_non_negative"):
        await db_session.flush()


@pytest.mark.parametrize("currency", ["eur", "EU", "EURO", "E1R"])
async def test_currency_must_be_three_uppercase_letters(
    db_session: AsyncSession, currency: str
) -> None:
    product, retailer = await _product_and_retailer(db_session)
    db_session.add(_offer(product, retailer, currency=currency))

    with pytest.raises(Exception, match=r"currency_iso|value too long"):
        await db_session.flush()


async def test_unknown_stock_state_is_rejected(db_session: AsyncSession) -> None:
    product, retailer = await _product_and_retailer(db_session)

    # Raw SQL on purpose: the ORM enum type would reject the value in Python first,
    # and this test must prove the database CHECK constraint does it by itself.
    with pytest.raises(IntegrityError, match="stock_state"):
        await db_session.execute(
            text(
                "INSERT INTO product_offer (id, product_id, retailer_id, price, currency, url,"
                " stock_state, source, last_checked_at, content_hash)"
                " VALUES (:id, :product_id, :retailer_id, 1.00, 'EUR', 'https://x.example',"
                " 'sold_out', 'fixture', now(), :hash)"
            ),
            {
                "id": uuid.uuid7(),
                "product_id": product.id,
                "retailer_id": retailer.id,
                "hash": "0" * 64,
            },
        )


async def test_one_offer_per_product_and_retailer(db_session: AsyncSession) -> None:
    product, retailer = await _product_and_retailer(db_session)
    db_session.add_all([_offer(product, retailer), _offer(product, retailer)])

    with pytest.raises(IntegrityError, match="uq_product_offer_product_retailer"):
        await db_session.flush()


async def test_retailer_domain_is_unique(db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            Retailer(name="Shop A", domain="same.example"),
            Retailer(name="Shop B", domain="same.example"),
        ]
    )

    with pytest.raises(IntegrityError, match="uq_retailer_domain"):
        await db_session.flush()


async def test_deleting_a_product_deletes_its_offers(db_session: AsyncSession) -> None:
    product, retailer = await _product_and_retailer(db_session)
    db_session.add(_offer(product, retailer))
    await db_session.flush()

    await db_session.delete(product)
    await db_session.flush()

    remaining = (await db_session.scalars(select(ProductOffer))).all()
    assert remaining == []
