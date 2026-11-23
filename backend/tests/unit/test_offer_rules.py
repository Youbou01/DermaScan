"""Unit tests for the pure offer rules (no database)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.modules.offers.enums import StockState
from app.modules.offers.models import ProductOffer, Retailer
from app.modules.offers.service import build_offer_list

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
STALE_AFTER = timedelta(days=7)
PRODUCT_ID = uuid.uuid4()


def _row(
    name: str,
    price: str,
    *,
    currency: str = "EUR",
    stock: StockState = StockState.IN_STOCK,
    age_days: float = 0,
    offer_id: uuid.UUID | None = None,
) -> tuple[ProductOffer, Retailer]:
    retailer = Retailer(
        id=uuid.uuid4(),
        name=name,
        domain=f"{name.lower().replace(' ', '-')}.example",
        is_affiliate=False,
    )
    offer = ProductOffer(
        id=offer_id or uuid.uuid4(),
        product_id=PRODUCT_ID,
        retailer_id=retailer.id,
        price=Decimal(price),
        currency=currency,
        url=f"https://{retailer.domain}/p/1",
        stock_state=stock,
        source="fixture",
        last_checked_at=NOW - timedelta(days=age_days),
        content_hash="0" * 64,
    )
    return offer, retailer


def test_cheapest_is_the_lowest_eligible_price() -> None:
    rows = [_row("Shop A", "15.50"), _row("Shop B", "12.00"), _row("Shop C", "20.00")]

    result = build_offer_list(PRODUCT_ID, rows, NOW, STALE_AFTER)

    assert result.cheapest_offer_id == rows[1][0].id
    assert [o.is_cheapest for o in result.offers] == [True, False, False]
    assert [str(o.price) for o in result.offers] == ["12.00", "15.50", "20.00"]


def test_stale_offer_is_labelled_and_never_cheapest() -> None:
    stale = _row("Shop Old", "5.00", age_days=8)
    fresh = _row("Shop New", "9.00")

    result = build_offer_list(PRODUCT_ID, [stale, fresh], NOW, STALE_AFTER)

    assert result.cheapest_offer_id == fresh[0].id
    by_name = {o.retailer.name: o for o in result.offers}
    assert by_name["Shop Old"].freshness == "stale"
    assert by_name["Shop Old"].is_cheapest is False
    assert by_name["Shop New"].freshness == "fresh"


def test_only_stale_offers_means_no_cheapest() -> None:
    result = build_offer_list(PRODUCT_ID, [_row("Shop Old", "5.00", age_days=30)], NOW, STALE_AFTER)

    assert result.cheapest_offer_id is None
    assert result.mixed_currencies is False
    assert result.offers[0].freshness == "stale"


def test_out_of_stock_and_unknown_are_never_cheapest() -> None:
    rows = [
        _row("Shop Out", "1.00", stock=StockState.OUT_OF_STOCK),
        _row("Shop Unknown", "2.00", stock=StockState.UNKNOWN),
        _row("Shop In", "9.00"),
    ]

    result = build_offer_list(PRODUCT_ID, rows, NOW, STALE_AFTER)

    assert result.cheapest_offer_id == rows[2][0].id
    assert next(o.retailer.name for o in result.offers) == "Shop In"


def test_mixed_currencies_among_eligible_offers_means_no_cheapest() -> None:
    rows = [_row("Shop A", "10.00"), _row("Shop B", "8.00", currency="USD")]

    result = build_offer_list(PRODUCT_ID, rows, NOW, STALE_AFTER)

    assert result.mixed_currencies is True
    assert result.cheapest_offer_id is None
    assert not any(o.is_cheapest for o in result.offers)


def test_currency_of_an_ineligible_offer_does_not_cause_mixed_currencies() -> None:
    rows = [_row("Shop A", "10.00"), _row("Shop B", "8.00", currency="USD", age_days=10)]

    result = build_offer_list(PRODUCT_ID, rows, NOW, STALE_AFTER)

    assert result.mixed_currencies is False
    assert result.cheapest_offer_id == rows[0][0].id


def test_no_offers_gives_an_empty_list() -> None:
    result = build_offer_list(PRODUCT_ID, [], NOW, STALE_AFTER)

    assert result.offers == []
    assert result.cheapest_offer_id is None
    assert result.mixed_currencies is False


def test_price_tie_is_broken_by_retailer_name_then_id() -> None:
    low_id = uuid.UUID("00000000-0000-7000-8000-000000000001")
    high_id = uuid.UUID("00000000-0000-7000-8000-000000000002")
    rows = [
        _row("Zed", "10.00"),
        _row("Same", "10.00", offer_id=high_id),
        _row("Same", "10.00", offer_id=low_id),
    ]

    result = build_offer_list(PRODUCT_ID, rows, NOW, STALE_AFTER)

    assert [o.id for o in result.offers][:2] == [low_id, high_id]
    assert result.cheapest_offer_id == low_id


def test_eligible_offers_come_before_the_others() -> None:
    rows = [
        _row("Shop Old", "1.00", age_days=9),
        _row("Shop Out", "2.00", stock=StockState.OUT_OF_STOCK),
        _row("Shop In", "50.00"),
    ]

    result = build_offer_list(PRODUCT_ID, rows, NOW, STALE_AFTER)

    assert [o.retailer.name for o in result.offers] == ["Shop In", "Shop Old", "Shop Out"]
