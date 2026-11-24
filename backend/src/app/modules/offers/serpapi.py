"""Real price source: Google Shopping results through SerpApi (https://serpapi.com)."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from statistics import median
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
_ATTEMPTS = 3
# Words that mark a different listing (gift, pack...) unless the product name has them too.
_EXTRA_WORDS = {"gift", "cadeau", "free", "gratuit", "pack", "coffret", "kit", "mini", "sample"}


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


_SERPAPI_PREFIX = "https://serpapi.com/"


def _text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return value if isinstance(value, str) else ""


def _stock(details: object) -> StockState:
    """Google writes 'En stock en ligne' in the offer details; anything else is unknown."""
    return StockState.IN_STOCK if "en stock" in _text(details).lower() else StockState.UNKNOWN


def _tokens(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return {t for t in re.findall(r"[a-z0-9]+", plain) if len(t) >= 3 or t.isdigit()}


def _matches(wanted: set[str], title: object) -> bool:
    """True when the result title contains every distinctive word of the product name."""
    if not wanted or not isinstance(title, str):
        return False
    found = _tokens(title)
    return wanted <= found and not ((found & _EXTRA_WORDS) - wanted)


def _amount(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None
    try:
        price = Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return price if price > 0 else None


def parse_stores(data: dict[str, Any]) -> list[RawOffer]:
    """Turn a SerpApi immersive-product response into offers: one per shop, cheapest first.

    Shops without a direct link, a known currency or a positive price are skipped.
    The price is the item price (shipping is not included).
    """
    product = data.get("product_results")
    block = product.get("stores") if isinstance(product, dict) else None
    rows: list[Any] = block if isinstance(block, list) else []

    best: dict[str, RawOffer] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        link = row.get("link")
        name = row.get("name")
        if not (isinstance(link, str) and isinstance(name, str) and name.strip()):
            continue
        host = _host(link)
        currency = _currency(row.get("price"))
        price = _amount(row.get("extracted_price"))
        if host is None or _is_google(host) or currency is None or price is None:
            continue
        offer = RawOffer(
            retailer_name=name.strip(),
            retailer_domain=host,
            price=price,
            currency=currency,
            url=link,
            stock_state=_stock(row.get("details_and_offers")),
        )
        current = best.get(host)
        if current is None or offer.price < current.price:
            best[host] = offer
    offers = list(best.values())
    if offers:
        # A price far from the typical one is almost surely another product or pack size.
        typical = median(o.price for o in offers)
        offers = [o for o in offers if typical / 2 <= o.price <= typical * 2]
    return sorted(offers, key=lambda o: (o.price, o.retailer_name))[:_MAX_OFFERS]


class SerpApiAdapter:
    """Finds the product on Google Shopping by name, then reads its stores (2 searches).

    Only a result whose title contains every distinctive word of the product name is used:
    no offers are better than the offers of another product.
    """

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        gl: str = "fr",
        hl: str = "fr",
        google_domain: str = "google.fr",
        location: str = "France",
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._gl = gl
        self._hl = hl
        self._google_domain = google_domain
        self._location = location
        self._timeout = timeout

    async def fetch_offers(self, barcode: str, product_name: str) -> list[RawOffer]:
        # Google Shopping has no barcode lookup: a barcode query returns unrelated products.
        del barcode
        query = product_name.strip()
        wanted = _tokens(query)
        # A category path or fewer than 3 distinctive words identifies no product.
        if "/" in query or len(wanted) < 3:
            return []
        # Google Shopping results are unstable (the same query sometimes returns unrelated
        # products), so a search without any matching row is repeated, skipping the cache.
        candidates: list[Any] = []
        for attempt in range(_ATTEMPTS):
            data = await self._search(query, fresh=attempt > 0)
            rows = data.get("shopping_results")
            if isinstance(rows, list):
                candidates = [
                    row
                    for row in rows
                    if isinstance(row, dict)
                    and _matches(wanted, row.get("title"))
                    and str(row.get("serpapi_immersive_product_api", "")).startswith(
                        _SERPAPI_PREFIX
                    )
                ]
            if candidates:
                break
        if not candidates:
            return []
        # Prefer a listing sold by several shops (the best-known one); ties keep Google's order.
        chosen = max(candidates, key=lambda row: row.get("multiple_sources") is True)
        url = httpx.URL(chosen["serpapi_immersive_product_api"]).copy_merge_params(
            {"more_stores": "true", "api_key": self._api_key}
        )
        return parse_stores(await self._get(url))

    async def _search(self, query: str, *, fresh: bool = False) -> dict[str, Any]:
        params: dict[str, str] = {
            "engine": "google_shopping",
            "q": query,
            "gl": self._gl,
            "hl": self._hl,
            "google_domain": self._google_domain,
            "location": self._location,
            "api_key": self._api_key,
        }
        if fresh:
            params["no_cache"] = "true"
        return await self._get(SERPAPI_URL, params)

    async def _get(
        self, url: str | httpx.URL, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        try:
            if self._client is not None:
                response = await self._client.get(url, params=params)
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url, params=params)
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
