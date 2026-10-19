# ruff: noqa: E402, S108, ASYNC240
import argparse
import asyncio
import gzip
import json
import logging
import sys
from itertools import islice
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.modules.ingestion.importer import import_product_record
from app.modules.ingredients.service import IngredientService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_DUMP_PATH = Path("/tmp/openbeautyfacts-products.jsonl.gz")
COMMIT_EVERY = 100


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Open Beauty Facts products.")
    parser.add_argument(
        "--dump-path",
        type=Path,
        default=DEFAULT_DUMP_PATH,
        help=f"Path to the OBF .jsonl.gz dump (default: {DEFAULT_DUMP_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help="Stop after N non-empty dump lines (for quick tests). Default: read everything.",
    )
    return parser.parse_args(argv)


async def main(dump_path: Path, limit: int | None) -> int:
    if not dump_path.exists():
        logger.error("OBF dump file not found at %s. Run E1 spike first.", dump_path)
        return 1

    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    logger.info("Starting OBF batch import (limit=%s)...", limit if limit else "none")
    imported_count = 0
    error_count = 0

    async with session_factory() as db:
        ingredient_service = IngredientService(db)

        with gzip.open(dump_path, "rt", encoding="utf-8", errors="ignore") as f:
            non_blank = ((n, ln) for n, ln in enumerate(f, start=1) if ln.strip())
            for line_no, line in islice(non_blank, limit):
                try:
                    row = json.loads(line)
                    success = await import_product_record(db, row, ingredient_service)
                    if success:
                        imported_count += 1
                        if imported_count % COMMIT_EVERY == 0:
                            await db.commit()
                            logger.info("Imported %d products so far...", imported_count)
                except Exception as exc:
                    error_count += 1
                    if error_count <= 10:
                        logger.warning("Error importing row %d: %s", line_no, exc)

            await db.commit()

    logger.info("Import complete! Imported: %d, Errors/Skipped: %d", imported_count, error_count)
    await engine.dispose()
    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(asyncio.run(main(args.dump_path, args.limit)))
