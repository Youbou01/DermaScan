"""CLI job to rematch unmatched product ingredients and recompute dirty/stale product scores."""

import asyncio
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.modules.catalog import CatalogService
from app.modules.scoring import SCORING_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def rematch_all_unmatched(db: AsyncSession, batch_size: int = 500) -> int:
    """Repeatedly rematches unmatched product ingredients until no more matches are found."""
    catalog_service = CatalogService(db)
    total_rematched = 0
    while True:
        count = await catalog_service.rematch_unmatched(batch_size=batch_size)
        if count == 0:
            break
        await db.commit()
        total_rematched += count
        logger.info("Rematched batch of %d ingredient rows (total %d)", count, total_rematched)
    return total_rematched


async def rescore_all_dirty(db: AsyncSession, batch_size: int = 100) -> int:
    """Repeatedly rescores products flagged score_dirty or with outdated scoring_version."""
    catalog_service = CatalogService(db)
    total_rescored = 0
    while True:
        count = await catalog_service.recompute_dirty_scores(batch_size=batch_size)
        if count == 0:
            break
        await db.commit()
        total_rescored += count
        logger.info(
            "Rescored batch of %d products for version %d (total %d)",
            count,
            SCORING_VERSION,
            total_rescored,
        )
    return total_rescored


async def main() -> None:
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    logger.info("Starting rematch and score recomputation job (Scoring v%d)...", SCORING_VERSION)

    async with session_factory() as db:
        rematched = await rematch_all_unmatched(db)
        rescored = await rescore_all_dirty(db)

    logger.info(
        "Job completed. Rematched ingredients: %d. Rescored products: %d.",
        rematched,
        rescored,
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
