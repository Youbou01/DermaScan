import asyncio
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.modules.scoring.service import recompute_stale_products

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    logger.info("Starting score recomputation CLI job...")
    total_updated = 0

    async with session_factory() as db:
        while True:
            count = await recompute_stale_products(db, batch_size=200)
            if count == 0:
                break
            total_updated += count

    logger.info("Recomputation complete. Total products updated: %d", total_updated)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
