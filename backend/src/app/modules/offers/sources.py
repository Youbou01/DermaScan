"""Price sources: the adapter interface and the deterministic fixture adapter."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.modules.catalog import compute_check_digit
from app.modules.offers.enums import StockState


@dataclass(frozen=True, slots=True)
class RawOffer:
    """One shop's offer as returned by a price source (not yet stored)."""

    retailer_name: str
    retailer_domain: str
    price: Decimal
    currency: str
    url: str
    stock_state: StockState = StockState.IN_STOCK
    # How old the price already is at the source. The refresh task derives last_checked_at
    # from it, so a "stale" demo offer stays stale whenever the fixture is used.
    age_days: float = 0


class PriceSourceAdapter(Protocol):
    async def fetch_offers(self, barcode: str, product_name: str) -> list[RawOffer]: ...


def _barcode(body: str) -> str:
    return body + str(compute_check_digit(body))


# Demo barcodes (bodies match scripts/seed_demo.py; the 4th has no seeded product).
FIXTURE_NORMAL = _barcode("619000000001")
FIXTURE_STALE = _barcode("619000000002")
FIXTURE_MIXED_CURRENCIES = _barcode("619000000003")
FIXTURE_NO_OFFERS = _barcode("619000000004")


def _offer(
    barcode: str,
    name: str,
    domain: str,
    price: str,
    currency: str = "EUR",
    *,
    stock: StockState = StockState.IN_STOCK,
    age_days: float = 0,
) -> RawOffer:
    return RawOffer(
        retailer_name=name,
        retailer_domain=domain,
        price=Decimal(price),
        currency=currency,
        url=f"https://{domain}/p/{barcode}",
        stock_state=stock,
        age_days=age_days,
    )


class FixtureAdapter:
    """Deterministic DEMO prices keyed by barcode. Not real data."""

    async def fetch_offers(self, barcode: str, product_name: str) -> list[RawOffer]:
        del product_name
        if barcode == FIXTURE_NORMAL:
            return [
                _offer(barcode, "Shop A", "shop-a.example", "15.50"),
                _offer(barcode, "Shop B", "shop-b.example", "12.00"),
                _offer(barcode, "Shop C", "shop-c.example", "20.00"),
            ]
        if barcode == FIXTURE_STALE:
            return [
                _offer(barcode, "Shop A", "shop-a.example", "9.00"),
                _offer(barcode, "Shop Old", "shop-old.example", "5.00", age_days=10),
            ]
        if barcode == FIXTURE_MIXED_CURRENCIES:
            return [
                _offer(barcode, "Shop A", "shop-a.example", "10.00"),
                _offer(barcode, "Shop US", "shop-us.example", "8.00", "USD"),
            ]
        if barcode == FIXTURE_NO_OFFERS:
            return []
        return [
            _offer(barcode, "Shop A", "shop-a.example", "14.90"),
            _offer(barcode, "Shop B", "shop-b.example", "13.20"),
        ]
