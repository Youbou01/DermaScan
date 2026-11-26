"""Background task: refresh the offers of one product (registered by the worker)."""

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.jobs import register_task
from app.modules.catalog import CatalogService, ProductNotFoundError
from app.modules.offers.refresh import refresh_product_offers
from app.modules.offers.serpapi import SerpApiAdapter
from app.modules.offers.sources import FixtureAdapter, PriceSourceAdapter

logger = structlog.get_logger(__name__)


def search_name(name: str, brand: str | None) -> str:
    """Brand plus name, so that a generic name does not match another brand's product."""
    clean = (brand or "").strip()
    if clean and clean.lower() not in name.lower():
        return f"{clean} {name}"
    return name


def build_price_source(settings: Settings) -> PriceSourceAdapter | None:
    """One source per run, chosen by PRICE_SOURCE. No automatic fallback between sources."""
    if settings.price_source == "fixture":
        return FixtureAdapter()
    if settings.price_source == "serpapi" and settings.serpapi_api_key:
        return SerpApiAdapter(settings.serpapi_api_key)
    return None  # "serpapi" selected but SERPAPI_API_KEY is missing


@register_task("refresh_offers")
async def refresh_offers_task(payload: dict[str, Any], session: AsyncSession) -> None:
    raw_id = payload.get("product_id")
    if not raw_id:
        logger.warning("refresh_offers_missing_id")
        return
    product_id = uuid.UUID(str(raw_id))

    settings = get_settings()
    adapter = build_price_source(settings)
    if adapter is None:
        logger.error("refresh_offers_source_unavailable", source=settings.price_source)
        return

    try:
        product = await CatalogService(session).get_product_detail(product_id, locale="en")
    except ProductNotFoundError:
        logger.warning("refresh_offers_product_not_found", product_id=str(product_id))
        return

    await refresh_product_offers(
        session,
        product_id=product_id,
        barcode=product.barcode,
        product_name=search_name(product.name, product.brand),
        adapter=adapter,
        source=settings.price_source,
    )
