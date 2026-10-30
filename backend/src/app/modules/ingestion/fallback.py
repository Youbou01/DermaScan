"""Async Open Beauty Facts fallback client with retries and negative caching."""

import asyncio
import random
from datetime import timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, ProductDetail
from app.modules.catalog.gtin import normalize_gtin
from app.modules.ingestion.importer import import_product_record
from app.modules.ingestion.sources.obf import OBFSourceAdapter, store_raw_product
from app.modules.ingredients import IngredientService

logger = structlog.get_logger(__name__)

OBF_PRODUCT_URL = "https://world.openbeautyfacts.org/api/v2/product/{barcode}.json"
USER_AGENT = "DermaScan-LiveFallback/1.0 (Free Academic Skincare Engine)"
NEGATIVE_CACHE_DURATION = timedelta(hours=24)


class OBFAsyncFallbackClient:
    """Async HTTP client for Open Beauty Facts API with retries and exponential backoff."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        clean_barcode = barcode.strip()
        url = OBF_PRODUCT_URL.format(barcode=clean_barcode)
        headers = {"User-Agent": USER_AGENT}

        max_retries = 2
        base_delay = 0.5

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=5.0)

        try:
            for attempt in range(max_retries + 1):
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == 1 and "product" in data:
                            prod = data["product"]
                            if isinstance(prod, dict):
                                return prod
                        return None
                    if resp.status_code == 404:
                        return None

                    if attempt < max_retries and (
                        resp.status_code >= 500 or resp.status_code == 429
                    ):
                        jitter = random.uniform(0.1, 0.3)  # noqa: S311
                        delay = base_delay * (2**attempt) + jitter
                        await asyncio.sleep(delay)
                        continue
                    return None
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt < max_retries:
                        jitter = random.uniform(0.1, 0.3)  # noqa: S311
                        delay = base_delay * (2**attempt) + jitter
                        logger.warning(
                            "obf_fallback_retry",
                            barcode=barcode,
                            attempt=attempt,
                            error=str(exc),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.warning("obf_fallback_timeout", barcode=barcode, error=str(exc))
                        return None
        finally:
            if owns_client:
                await client.aclose()

        return None


async def fetch_remote_product_by_barcode(
    barcode: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any] | None:
    return await OBFAsyncFallbackClient(client).fetch_product_by_barcode(barcode)


async def handle_barcode_miss_fallback(
    session: AsyncSession,
    barcode: str,
    locale: str = "en",
    client: httpx.AsyncClient | None = None,
) -> ProductDetail | None:
    """Fallback handler called when a barcode is missing in local DB.

    1. Checks barcode_miss negative cache (<24h).
    2. Queries OBF API asynchronously with retries.
    3. If found, maps, validates, imports, and returns ProductDetail.
    4. If not found, records in barcode_miss.
    """
    try:
        gtin = normalize_gtin(barcode)
    except Exception:
        return None

    catalog_service = CatalogService(session)

    # Check negative cache before making external network calls
    is_cached = await catalog_service.is_barcode_miss_negative_cached(
        gtin, duration=NEGATIVE_CACHE_DURATION
    )
    if is_cached:
        await catalog_service.record_barcode_miss(gtin)
        return None

    # Query OBF
    obf_client = OBFAsyncFallbackClient(client=client)
    prod_data = await obf_client.fetch_product_by_barcode(gtin)

    if prod_data is not None:
        adapter = OBFSourceAdapter()
        raw_record = adapter.to_raw(prod_data)
        await store_raw_product(session, raw_record)

        ingredient_service = IngredientService(session)
        success = await import_product_record(
            session,
            prod_data,
            ingredient_service=ingredient_service,
            catalog_service=catalog_service,
        )
        if success:
            await session.commit()
            return await catalog_service.get_product_detail_by_barcode(gtin, locale)

    # Miss or import failure: record in barcode_miss
    await catalog_service.record_barcode_miss(gtin)
    return None
