"""Refresh the stored offers of one product from a price source."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.offers.repository import OfferRepository
from app.modules.offers.sources import PriceSourceAdapter, RawOffer

logger = structlog.get_logger(__name__)


def compute_content_hash(offer: RawOffer) -> str:
    """Hash of the data a shopper sees; unchanged hash means only the check time moves."""
    raw = "|".join((f"{offer.price:.2f}", offer.currency, offer.url, offer.stock_state.value))
    return hashlib.sha256(raw.encode()).hexdigest()


async def refresh_product_offers(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    barcode: str,
    product_name: str,
    adapter: PriceSourceAdapter,
    source: str,
    now: datetime | None = None,
) -> int:
    """Fetch offers and upsert them. Returns how many were stored.

    A failing or empty source keeps the existing offers (they simply become stale)
    and never raises, so the worker does not retry a source outage.
    """
    checked_at = now or datetime.now(UTC)
    try:
        raw_offers = await adapter.fetch_offers(barcode, product_name)
    except Exception:
        logger.exception("offers_source_failed", product_id=str(product_id), source=source)
        return 0

    repository = OfferRepository(session)
    stored = 0
    for raw in raw_offers:
        retailer = await repository.upsert_retailer(
            name=raw.retailer_name, domain=raw.retailer_domain
        )
        await repository.upsert_offer(
            product_id=product_id,
            retailer_id=retailer.id,
            price=raw.price,
            currency=raw.currency,
            url=raw.url,
            stock_state=raw.stock_state,
            source=source,
            last_checked_at=checked_at - timedelta(days=raw.age_days),
            content_hash=compute_content_hash(raw),
        )
        stored += 1
    logger.info("offers_refreshed", product_id=str(product_id), source=source, stored=stored)
    return stored
