"""Real price source: Google Shopping results through SerpApi (https://serpapi.com)."""

from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from app.modules.offers.enums import StockState
from app.modules.offers.sources import RawOffer

logger = structlog.get_logger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"
_CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP"}
_MAX_OFFERS = 10


class SerpApiError(Exception):
    """The SerpApi request failed. The message never contains the API key."""


def _host(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host or None


def _is_google(host: str) -> bool:
    return "google" in host.split(".")


def _currency(price_text: object) -> str | None:
    if not isinstance(price_text, str):
        return None
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in price_text:
            return code
    return None


def parse_results(data: dict[str, Any]) -> list[RawOffer]:
    """Turn a SerpApi response into offers: one per shop domain, cheapest first.

    Google Shopping gives no stock information, so every listed offer counts as in stock.
    Rows without a direct shop link, a known currency or a positive price are skipped.
    """
    rows: list[Any] = []
    for key in ("shopping_results", "inline_shopping_results"):
        block = data.get(key)
        if isinstance(block, list):
            rows.extend(block)

    best: dict[str, RawOffer] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        link = row.get("link")
        source = row.get("source")
        amount = row.get("extracted_price")
        if not (isinstance(link, str) and isinstance(source, str) and source.strip()):
            continue
        if isinstance(amount, bool) or not isinstance(amount, int | float):
            continue
        host = _host(link)
        currency = _currency(row.get("price"))
        if host is None or _is_google(host) or currency is None:
            continue
        try:
            price = Decimal(str(amount)).quantize(Decimal("0.01"))
        except InvalidOperation:
            continue
        if price <= 0:
            continue
        offer = RawOffer(
            retailer_name=source.strip(),
            retailer_domain=host,
            price=price,
            currency=currency,
            url=link,
            stock_state=StockState.IN_STOCK,
        )
        current = best.get(host)
        if current is None or offer.price < current.price:
            best[host] = offer
    return sorted(best.values(), key=lambda o: (o.price, o.retailer_name))[:_MAX_OFFERS]


class SerpApiAdapter:
    """Searches Google Shopping by barcode first, then by product name."""

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        gl: str = "fr",
        hl: str = "fr",
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._gl = gl
        self._hl = hl
        self._timeout = timeout

    async def fetch_offers(self, barcode: str, product_name: str) -> list[RawOffer]:
        for query in (barcode, product_name):
            if not query.strip():
                continue
            offers = parse_results(await self._search(query))
            if offers:
                return offers
        return []

    async def _search(self, query: str) -> dict[str, Any]:
        params = {
            "engine": "google_shopping",
            "q": query,
            "gl": self._gl,
            "hl": self._hl,
            "api_key": self._api_key,
        }
        try:
            if self._client is not None:
                response = await self._client.get(SERPAPI_URL, params=params)
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(SERPAPI_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # httpx messages contain the request URL, which holds the API key: do not chain.
            raise SerpApiError(f"SerpApi request failed ({type(exc).__name__})") from None
        if not isinstance(data, dict):
            raise SerpApiError("SerpApi returned an unexpected response")
        if "error" in data:
            logger.info("serpapi_no_results", detail=str(data["error"])[:200])
            return {}
        return data
