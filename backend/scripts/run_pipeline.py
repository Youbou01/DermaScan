"""Run end-to-end ingestion and enrichment pipeline over raw_product records."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Ensure task handlers are registered
import app.modules.catalog.tasks
import app.modules.enrichment.tasks
import app.modules.ingestion.tasks  # noqa: F401
from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.core.jobs import enqueue_job, execute_job, fetch_and_lock_next_job
from app.modules.ingestion.models import RawProduct

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pipeline over raw_product records.")
    parser.add_argument(
        "--source",
        type=str,
        default="open_beauty_facts",
        help="Raw product source filter.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum raw records to enqueue.",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Process enqueued jobs in-process until finished.",
    )
    return parser.parse_args(argv)


async def enqueue_raw_products(session: AsyncSession, source: str, limit: int) -> int:
    stmt = select(RawProduct.id)
    if source != "all":
        stmt = stmt.where(RawProduct.source == source)
    stmt = stmt.order_by(RawProduct.fetched_at.desc()).limit(limit)

    raw_ids = (await session.execute(stmt)).scalars().all()
    count = 0
    for raw_id in raw_ids:
        await enqueue_job(
            session,
            queue="enrichment",
            task_name="enrich_raw_product",
            payload={"raw_product_id": str(raw_id)},
        )
        count += 1
    await session.commit()
    logger.info("Enqueued %d enrich_raw_product jobs.", count)
    return count


async def run_worker_loop(
    session_factory: async_sessionmaker[AsyncSession], max_jobs: int = 500
) -> int:
    executed = 0
    queues = ["enrichment", "default"]

    while executed < max_jobs:
        job_found = False
        async with session_factory() as session:
            for q in queues:
                job = await fetch_and_lock_next_job(session, queue=q)
                if job is not None:
                    job_found = True
                    await execute_job(session, job)
                    await session.commit()
                    executed += 1
                    break
        if not job_found:
            break
    logger.info("Worker loop finished: executed %d jobs.", executed)
    return executed


async def main() -> None:
    args = parse_args()
    engine = create_engine(Settings())
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as session:
            enqueued = await enqueue_raw_products(session, args.source, args.limit)

        if args.worker and enqueued > 0:
            logger.info("Running in-process worker to execute enqueued jobs...")
            await run_worker_loop(session_factory, max_jobs=enqueued * 3)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
