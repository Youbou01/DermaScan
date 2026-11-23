#!/usr/bin/env python3
"""Enqueue refresh_offers jobs for products identified by barcode (the worker runs them)."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.core.errors import AppError
from app.core.jobs import enqueue_job
from app.modules.catalog import CatalogService
from app.modules.offers.sources import (
    FIXTURE_MIXED_CURRENCIES,
    FIXTURE_NO_OFFERS,
    FIXTURE_NORMAL,
    FIXTURE_STALE,
)

logger = logging.getLogger("refresh_offers")

DEMO_BARCODES = [FIXTURE_NORMAL, FIXTURE_STALE, FIXTURE_MIXED_CURRENCIES, FIXTURE_NO_OFFERS]


async def main(barcodes: list[str]) -> int:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    enqueued = 0
    try:
        async with session_factory() as session:
            catalog = CatalogService(session)
            for barcode in barcodes:
                try:
                    product = await catalog.get_product_detail_by_barcode(barcode, "en")
                except AppError as exc:
                    logger.warning("Skipping barcode %s: %s", barcode, exc)
                    continue
                await enqueue_job(
                    session, "refresh_offers", {"product_id": str(product.id)}, queue="default"
                )
                enqueued += 1
            await session.commit()
    finally:
        await engine.dispose()
    return enqueued


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("barcodes", nargs="*", help="GTIN-13 barcodes (default: demo barcodes)")
    args = parser.parse_args()
    count = asyncio.run(main(args.barcodes or DEMO_BARCODES))
    logger.info("Enqueued %d refresh_offers job(s)", count)
