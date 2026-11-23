import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.modules.offers.enums import StockState
from app.modules.offers.serpapi import SerpApiAdapter, SerpApiError, parse_results
from app.modules.offers.sources import FixtureAdapter
from app.modules.offers.tasks import build_price_source

NO_RESULTS = {"error": "Google hasn't returned any results for this query."}


def _row(source: str, amount: float, link: str, text: str | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "extracted_price": amount,
        "price": text if text is not None else f"{amount} €",
        "link": link,
    }


def _run(
    responses: dict[str, Any], barcode: str, name: str, status: int = 200
) -> tuple[list[SimpleNamespace] | list[Any], list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=responses.get(request.url.params["q"], NO_RESULTS))

    async def go() -> list[Any]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await SerpApiAdapter("test-key", client=client).fetch_offers(barcode, name)

    return asyncio.run(go()), seen


def test_parse_keeps_cheapest_direct_offer_per_shop() -> None:
    data = {
        "shopping_results": [
            _row("Shop A", 14, "https://shop-a.fr/p/2"),
            _row("Google Row", 9, "https://www.google.com/search?q=x"),
            _row("No Currency", 5, "https://nocur.fr/p", "5 TND"),
            _row("Shop B", 20, "https://www.shop-b.fr/p"),
        ],
        "inline_shopping_results": [_row("Shop A", 12.5, "https://www.shop-a.fr/p/1")],
    }
    offers = parse_results(data)
    assert [o.retailer_domain for o in offers] == ["shop-a.fr", "shop-b.fr"]
    assert [o.price for o in offers] == [Decimal("12.50"), Decimal("20.00")]
    assert {o.currency for o in offers} == {"EUR"}
    assert {o.stock_state for o in offers} == {StockState.IN_STOCK}


def test_barcode_is_searched_first_and_name_is_not_needed_when_it_matches() -> None:
    barcode = "3525727539406"
    responses = {barcode: {"shopping_results": [_row("Shop A", 10, "https://shop-a.fr/p")]}}
    offers, seen = _run(responses, barcode, "Some Cream")
    assert len(offers) == 1
    assert [r.url.params["q"] for r in seen] == [barcode]
    assert seen[0].url.params["engine"] == "google_shopping"
    assert seen[0].url.params["gl"] == "fr"


def test_falls_back_to_the_product_name_when_the_barcode_finds_nothing() -> None:
    responses = {"Some Cream": {"shopping_results": [_row("Shop A", 10, "https://shop-a.fr/p")]}}
    offers, seen = _run(responses, "3525727539406", "Some Cream")
    assert len(offers) == 1
    assert [r.url.params["q"] for r in seen] == ["3525727539406", "Some Cream"]


def test_no_results_gives_an_empty_list() -> None:
    offers, _ = _run({}, "3525727539406", "Some Cream")
    assert offers == []


def test_http_error_raises_without_leaking_the_api_key() -> None:
    with pytest.raises(SerpApiError) as excinfo:
        _run({}, "3525727539406", "Some Cream", status=500)
    assert "test-key" not in str(excinfo.value)


def test_build_price_source_follows_the_settings() -> None:
    def settings(source: str, key: str | None) -> Any:
        return SimpleNamespace(price_source=source, serpapi_api_key=key)

    assert isinstance(build_price_source(settings("fixture", None)), FixtureAdapter)
    assert isinstance(build_price_source(settings("serpapi", "k")), SerpApiAdapter)
    assert build_price_source(settings("serpapi", None)) is None
