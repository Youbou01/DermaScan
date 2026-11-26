"""Offer rules: eligibility, freshness and the cheapest price (computed at read time)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService
from app.modules.offers.enums import StockState
from app.modules.offers.models import ProductOffer, Retailer
from app.modules.offers.repository import OfferRepository
from app.modules.offers.schemas import OfferListOut, OfferOut, RetailerOut

DEFAULT_STALE_AFTER = timedelta(days=7)


def _is_fresh(offer: ProductOffer, now: datetime, stale_after: timedelta) -> bool:
    return offer.last_checked_at >= now - stale_after


def _is_eligible(offer: ProductOffer, now: datetime, stale_after: timedelta) -> bool:
    return _is_fresh(offer, now, stale_after) and offer.stock_state == StockState.IN_STOCK


def build_offer_list(
    product_id: uuid.UUID,
    rows: list[tuple[ProductOffer, Retailer]],
    now: datetime,
    stale_after: timedelta,
) -> OfferListOut:
    """Pure function: no database access, so every rule is unit-testable."""
    eligible = [row for row in rows if _is_eligible(row[0], now, stale_after)]
    others = [row for row in rows if not _is_eligible(row[0], now, stale_after)]

    def sort_key(row: tuple[ProductOffer, Retailer]) -> tuple[object, ...]:
        offer, retailer = row
        return (offer.price, retailer.name, str(offer.id))

    eligible.sort(key=sort_key)
    others.sort(key=sort_key)

    mixed_currencies = len({offer.currency for offer, _ in eligible}) > 1
    cheapest_id = eligible[0][0].id if eligible and not mixed_currencies else None

    offers = [
        OfferOut(
            id=offer.id,
            retailer=RetailerOut(
                name=retailer.name,
                domain=retailer.domain,
                logo_url=retailer.logo_url,
                is_affiliate=retailer.is_affiliate,
                affiliate_label=retailer.affiliate_label,
            ),
            price=offer.price,
            currency=offer.currency,
            url=offer.url,
            stock_state=offer.stock_state,
            freshness="fresh" if _is_fresh(offer, now, stale_after) else "stale",
            last_checked_at=offer.last_checked_at,
            is_cheapest=offer.id == cheapest_id,
        )
        for offer, retailer in [*eligible, *others]
    ]
    return OfferListOut(
        product_id=product_id,
        cheapest_offer_id=cheapest_id,
        mixed_currencies=mixed_currencies,
        offers=offers,
    )


class OfferService:
    def __init__(self, session: AsyncSession) -> None:
        self._catalog = CatalogService(session)
        self._offers = OfferRepository(session)

    async def list_offers(
        self,
        product_id: uuid.UUID,
        locale: str,
        stale_after: timedelta = DEFAULT_STALE_AFTER,
    ) -> OfferListOut:
        # Raises ProductNotFoundError (404) for an unknown product.
        await self._catalog.get_product_detail(product_id, locale)
        rows = await self._offers.list_for_product(product_id)
        return build_offer_list(product_id, rows, datetime.now(UTC), stale_after)
