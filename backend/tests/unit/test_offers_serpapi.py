import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.modules.offers.enums import StockState
from app.modules.offers.serpapi import (
    SerpApiAdapter,
    SerpApiError,
    _matches,
    parse_stores,
)
from app.modules.offers.sources import FixtureAdapter
from app.modules.offers.tasks import build_price_source, search_name

NO_RESULTS = {"error": "Google hasn't returned any results for this query."}


IMMERSIVE = "https://serpapi.com/search.json?engine=google_immersive_product&page_token=demo-value"
OTHER = IMMERSIVE.replace("demo-value", "other-value")
SHOPPING = {
    "shopping_results": [
        {"title": "Acme Day Cream 50 ml", "serpapi_immersive_product_api": IMMERSIVE}
    ]
}


def _store(
    name: str,
    amount: float,
    link: str,
    price: str | None = None,
    details: Any = "['En stock en ligne']",
) -> dict[str, Any]:
    return {
        "name": name,
        "extracted_price": str(amount),
        "price": price if price is not None else f"{amount} €",
        "link": link,
        "details_and_offers": details,
    }


def _run(
    shopping: dict[str, Any],
    immersive: dict[str, Any],
    name: str,
    status: int = 200,
    barcode: str = "3525727539406",
) -> tuple[list[Any], list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        params = request.url.params
        if params["engine"] == "google_immersive_product":
            return httpx.Response(status, json=immersive)
        return httpx.Response(status, json=shopping.get(params["q"], NO_RESULTS))

    async def go() -> list[Any]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await SerpApiAdapter("test-key", client=client).fetch_offers(barcode, name)

    return asyncio.run(go()), seen


def test_parse_keeps_cheapest_direct_offer_per_shop() -> None:
    data = {
        "product_results": {
            "stores": [
                _store("Shop A", 14, "https://shop-a.fr/p/2"),
                _store("Google Row", 9, "https://www.google.com/search?q=x"),
                _store("No Currency", 5, "https://nocur.fr/p", "5 TND"),
                _store("Shop B", 20, "https://www.shop-b.fr/p"),
                _store("Shop A", 12.5, "https://www.shop-a.fr/p/1"),
            ]
        }
    }
    offers = parse_stores(data)
    assert [o.retailer_domain for o in offers] == ["shop-a.fr", "shop-b.fr"]
    assert [o.price for o in offers] == [Decimal("12.50"), Decimal("20.00")]
    assert {o.currency for o in offers} == {"EUR"}


def test_stock_is_read_from_the_offer_details() -> None:
    data = {
        "product_results": {
            "stores": [
                _store("Shop A", 10, "https://shop-a.fr/p", details="['En stock en ligne']"),
                _store("Shop B", 11, "https://shop-b.fr/p", details=["En stock en ligne"]),
                _store("Shop C", 12, "https://shop-c.fr/p", details="['Livraison gratuite']"),
                _store("Shop D", 13, "https://shop-d.fr/p", details=None),
            ]
        }
    }
    states = {o.retailer_name: o.stock_state for o in parse_stores(data)}
    assert states == {
        "Shop A": StockState.IN_STOCK,
        "Shop B": StockState.IN_STOCK,
        "Shop C": StockState.UNKNOWN,
        "Shop D": StockState.UNKNOWN,
    }


def test_product_name_is_searched_then_the_stores_are_read() -> None:
    immersive = {"product_results": {"stores": [_store("Shop A", 10, "https://shop-a.fr/p")]}}
    offers, seen = _run({"Acme Day Cream": SHOPPING}, immersive, "Acme Day Cream")
    assert len(offers) == 1
    assert [r.url.params["engine"] for r in seen] == ["google_shopping", "google_immersive_product"]
    assert seen[0].url.params["q"] == "Acme Day Cream"
    assert seen[0].url.params["gl"] == "fr"
    second = seen[1].url.params
    assert second.get("page_token") == "demo-value"
    assert seen[1].url.params["more_stores"] == "true"
    assert "api_key" in seen[1].url.params


def test_no_results_gives_an_empty_list() -> None:
    offers, seen = _run({}, {}, "Acme Day Cream")
    assert offers == []
    assert len(seen) == 1


def test_empty_name_makes_no_request() -> None:
    offers, seen = _run({}, {}, "  ")
    assert offers == []
    assert seen == []


def test_a_link_outside_serpapi_is_never_followed() -> None:
    shopping = {
        "Acme Day Cream": {
            "shopping_results": [
                {
                    "title": "Acme Day Cream",
                    "serpapi_immersive_product_api": "https://evil.example/x",
                }
            ]
        }
    }
    offers, seen = _run(shopping, {}, "Acme Day Cream")
    assert offers == []
    assert len(seen) == 1


def test_a_row_that_does_not_match_the_product_name_is_skipped() -> None:
    other = {"title": "Garnier Olia 4", "serpapi_immersive_product_api": OTHER}
    offers, seen = _run({"Acme Day Cream": {"shopping_results": [other]}}, {}, "Acme Day Cream")
    assert offers == []
    assert len(seen) == 1


def test_the_first_matching_row_is_used_even_when_it_is_not_first() -> None:
    other = {"title": "Garnier Olia 4", "serpapi_immersive_product_api": OTHER}
    good = {"title": "Acme Day Cream 50 ml", "serpapi_immersive_product_api": IMMERSIVE}
    immersive = {"product_results": {"stores": [_store("Shop A", 10, "https://shop-a.fr/p")]}}
    shopping = {"Acme Day Cream": {"shopping_results": [other, good]}}
    offers, seen = _run(shopping, immersive, "Acme Day Cream")
    assert len(offers) == 1
    assert seen[1].url.params.get("page_token") == "demo-value"


def test_a_generic_or_category_name_makes_no_request() -> None:
    for name in ("Daily Moisture", "Beauté & Hygiène / Soins Du Corps / Déodorants"):
        offers, seen = _run({}, {}, name)
        assert offers == []
        assert seen == []


def test_search_name_adds_the_brand_once() -> None:
    assert search_name("Daily Moisture", "SkinCeuticals") == "SkinCeuticals Daily Moisture"
    assert search_name("Dove Daily Moisture", "Dove") == "Dove Daily Moisture"
    assert search_name("Daily Moisture", None) == "Daily Moisture"
    assert search_name("Daily Moisture", "  ") == "Daily Moisture"


def test_a_row_sold_by_several_shops_is_preferred() -> None:
    single = {"title": "Acme Day Cream 30 ml", "serpapi_immersive_product_api": IMMERSIVE}
    several = {
        "title": "Acme Day Cream 50 ml",
        "multiple_sources": True,
        "serpapi_immersive_product_api": OTHER,
    }
    immersive = {"product_results": {"stores": [_store("Shop A", 10, "https://shop-a.fr/p")]}}
    shopping = {"Acme Day Cream": {"shopping_results": [single, several]}}
    offers, seen = _run(shopping, immersive, "Acme Day Cream")
    assert len(offers) == 1
    assert seen[1].url.params.get("page_token") == "other-value"


def test_gift_and_pack_listings_do_not_match() -> None:
    wanted = {"acme", "day", "cream"}
    assert _matches(wanted, "Acme Day Cream 50 ml")
    assert not _matches(wanted, "Free Gift Acme Day Cream")
    assert not _matches(wanted, "Acme Day Cream coffret")


def test_prices_far_from_the_typical_one_are_dropped() -> None:
    data = {
        "product_results": {
            "stores": [
                _store("Shop A", 55, "https://shop-a.fr/p"),
                _store("Shop B", 57, "https://shop-b.fr/p"),
                _store("Shop C", 59, "https://shop-c.fr/p"),
                _store("Shop D", 513, "https://shop-d.fr/p"),
                _store("Shop E", 6, "https://shop-e.fr/p"),
            ]
        }
    }
    assert [o.retailer_name for o in parse_stores(data)] == ["Shop A", "Shop B", "Shop C"]


def test_http_error_raises_without_leaking_the_api_key() -> None:
    with pytest.raises(SerpApiError) as excinfo:
        _run({}, {}, "Acme Day Cream", status=500)
    assert "test-key" not in str(excinfo.value)


def test_build_price_source_follows_the_settings() -> None:
    def settings(source: str, key: str | None) -> Any:
        return SimpleNamespace(price_source=source, serpapi_api_key=key)

    assert isinstance(build_price_source(settings("fixture", None)), FixtureAdapter)
    assert isinstance(build_price_source(settings("serpapi", "k")), SerpApiAdapter)
    assert build_price_source(settings("serpapi", None)) is None
