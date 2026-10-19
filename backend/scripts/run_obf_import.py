# ruff: noqa: E402, S108, ASYNC240
import asyncio
import gzip
import json
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.modules.ingestion.importer import import_product_record
from app.modules.ingredients.service import IngredientService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DUMP_PATH = Path("/tmp/openbeautyfacts-products.jsonl.gz")


async def main() -> None:
    if not DUMP_PATH.exists():
        logger.error("OBF dump file not found at %s. Run E1 spike first.", DUMP_PATH)
        return

    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    logger.info("Starting OBF batch import (Tasks E2 & E3)...")
    imported_count = 0
    error_count = 0

    async with session_factory() as db:
        ingredient_service = IngredientService(db)

        with gzip.open(DUMP_PATH, "rt", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    success = await import_product_record(db, row, ingredient_service)
                    if success:
                        imported_count += 1
                        if imported_count % 100 == 0:
                            await db.commit()
                            logger.info("Imported %d products so far...", imported_count)
                except Exception as exc:
                    error_count += 1
                    if error_count <= 10:
                        logger.warning("Error importing row %d: %s", line_no, exc)

            await db.commit()

    logger.info("Import complete! Imported: %d, Errors/Skipped: %d", imported_count, error_count)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
