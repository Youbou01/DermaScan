#!/usr/bin/env python3
"""Streaming high-concurrency crawler & ingestion runner for https://pharma-shop.tn."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
import app.modules.catalog.tasks
import app.modules.enrichment.tasks
import app.modules.ingestion.tasks  # noqa: F401
from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.core.jobs import enqueue_job, run_pending_jobs
from app.modules.ingestion import IngestionService, store_raw_product
from app.modules.ingestion.models import ScrapeStaging
from app.modules.ingestion.sources.scraper import (
    GenericScraperAdapter,
    ScraperFetchError,
    canonicalize_url,
    load_site_config,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Streaming full-catalog scraper for https://pharma-shop.tn"
    )
    parser.add_argument("--limit", type=int, default=0, help="Max products (0 = UNLIMITED)")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent extraction workers")
    parser.add_argument(
        "--force-refresh", action="store_true", help="Re-scrape already extracted URLs"
    )
    parser.add_argument("--worker", action="store_true", help="Drain job queues after scraping")
    args = parser.parse_args()

    max_limit = args.limit if args.limit > 0 else None
    site_cfg = load_site_config("pharma_shop")
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    try:
        already_scraped: set[str] = set()
        if not args.force_refresh:
            async with session_factory() as session:
                rows = (
                    await session.scalars(
                        select(ScrapeStaging.url).where(
                            ScrapeStaging.status.in_(["extracted", "fetched"])
                        )
                    )
                ).all()
                already_scraped = {canonicalize_url(u) for u in rows}
            if already_scraped:
                logger.info(
                    "Checkpoint loaded: skipping %d already-scraped URLs.",
                    len(already_scraped),
                )

        async with session_factory() as session:
            ing_service = IngestionService(session)
            run = await ing_service.create_run(source="scrape:pharma_shop")
            run_id = run.id
            await session.commit()

        url_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=args.concurrency * 10)
        stats = {"enqueued": 0, "extracted": 0, "failed": 0}

        limits = httpx.Limits(
            max_connections=args.concurrency * 2,
            max_keepalive_connections=args.concurrency,
        )
        async with httpx.AsyncClient(
            timeout=site_cfg.timeout_seconds,
            follow_redirects=True,
            limits=limits,
        ) as http_client:
            adapter = GenericScraperAdapter(site_config=site_cfg, client=http_client)

            async def _producer() -> None:
                pending_batch = 0
                try:
                    async for url in adapter.discover(limit=max_limit):
                        if canonicalize_url(url) in already_scraped:
                            continue
                        await url_queue.put(url)
                        stats["enqueued"] += 1
                        pending_batch += 1
                        if pending_batch >= 50:
                            async with session_factory() as session:
                                await IngestionService(session).increment_run_counter(
                                    run_id, "enqueued", pending_batch
                                )
                                await session.commit()
                            pending_batch = 0
                except Exception as exc:
                    logger.error("Discovery stream error (continuing with queued URLs): %r", exc)
                finally:
                    if pending_batch > 0:
                        async with session_factory() as session:
                            await IngestionService(session).increment_run_counter(
                                run_id, "enqueued", pending_batch
                            )
                            await session.commit()
                    for _ in range(args.concurrency):
                        await url_queue.put(None)

            async def _consumer(worker_id: int) -> None:
                while True:
                    target_url = await url_queue.get()
                    if target_url is None:
                        url_queue.task_done()
                        break
                    try:
                        for attempt in range(1, 4):
                            try:
                                extracted = await adapter.fetch(target_url)
                                raw_rec = adapter.to_raw(extracted, url=target_url)
                                async with session_factory() as session:
                                    ing = IngestionService(session)
                                    await ing.stage_scrape(
                                        url=target_url,
                                        status="extracted",
                                        content_hash=raw_rec.content_hash,
                                        extracted_json=extracted,
                                        run_id=run_id,
                                    )
                                    raw_id = await store_raw_product(session, raw_rec)
                                    await ing.increment_run_counter(run_id, "fetched", 1)
                                    if raw_id is not None:
                                        await enqueue_job(
                                            session,
                                            queue="enrichment",
                                            task_name="enrich_raw_product",
                                            payload={
                                                "raw_product_id": str(raw_id),
                                                "run_id": str(run_id),
                                            },
                                        )
                                    await session.commit()
                                stats["extracted"] += 1
                                if stats["extracted"] % 50 == 0:
                                    logger.info(
                                        "Stream progress: %d extracted / %d discovered",
                                        stats["extracted"],
                                        stats["enqueued"],
                                    )
                                break
                            except (
                                ScraperFetchError,
                                httpx.HTTPError,
                                TimeoutError,
                            ) as exc:
                                if attempt == 3:
                                    stats["failed"] += 1
                                    logger.warning(
                                        "Worker %d failed %s: %s",
                                        worker_id,
                                        target_url,
                                        exc,
                                    )
                                    async with session_factory() as session:
                                        await IngestionService(session).increment_run_counter(
                                            run_id, "failed", 1
                                        )
                                        await session.commit()
                                else:
                                    await asyncio.sleep(1.5 * attempt)
                    finally:
                        url_queue.task_done()

            await asyncio.gather(
                _producer(),
                *(_consumer(i) for i in range(args.concurrency)),
            )

        logger.info(
            "Streaming crawl finished! Discovered=%d, Extracted=%d, Failed=%d",
            stats["enqueued"],
            stats["extracted"],
            stats["failed"],
        )

        if args.worker:
            logger.info("Draining enrichment and default job queues...")
            while True:
                ran = 0
                async with session_factory() as session:
                    ran += await run_pending_jobs(session, queue="enrichment", limit=250)
                    ran += await run_pending_jobs(session, queue="default", limit=250)
                if ran == 0:
                    break
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
