"""Unit tests for the fixture price source (no database, no network)."""

from decimal import Decimal

from app.modules.catalog import normalize_gtin
from app.modules.offers.sources import (
    FIXTURE_MIXED_CURRENCIES,
    FIXTURE_NO_OFFERS,
    FIXTURE_NORMAL,
    FIXTURE_STALE,
    FixtureAdapter,
)


def test_demo_barcodes_are_valid_gtin13() -> None:
    for code in (FIXTURE_NORMAL, FIXTURE_STALE, FIXTURE_MIXED_CURRENCIES, FIXTURE_NO_OFFERS):
        assert normalize_gtin(code) == code
    assert FIXTURE_NORMAL == "6190000000019"


async def test_normal_barcode_has_three_eur_shops() -> None:
    offers = await FixtureAdapter().fetch_offers(FIXTURE_NORMAL, "Soft Day Cream")

    assert len(offers) == 3
    assert {o.currency for o in offers} == {"EUR"}
    assert min(o.price for o in offers) == Decimal("12.00")
    assert all(o.age_days == 0 for o in offers)


async def test_stale_barcode_has_an_old_offer() -> None:
    offers = await FixtureAdapter().fetch_offers(FIXTURE_STALE, "x")

    assert sorted(o.age_days for o in offers) == [0, 10]


async def test_mixed_currency_barcode_has_two_currencies() -> None:
    offers = await FixtureAdapter().fetch_offers(FIXTURE_MIXED_CURRENCIES, "x")

    assert {o.currency for o in offers} == {"EUR", "USD"}


async def test_no_offers_barcode_is_empty() -> None:
    assert await FixtureAdapter().fetch_offers(FIXTURE_NO_OFFERS, "x") == []


async def test_other_barcodes_get_the_default_set_with_their_own_urls() -> None:
    offers = await FixtureAdapter().fetch_offers("5901234123457", "x")

    assert len(offers) == 2
    assert all(o.url.endswith("/p/5901234123457") for o in offers)


async def test_fixture_is_deterministic() -> None:
    adapter = FixtureAdapter()

    assert await adapter.fetch_offers(FIXTURE_NORMAL, "x") == await adapter.fetch_offers(
        FIXTURE_NORMAL, "y"
    )
