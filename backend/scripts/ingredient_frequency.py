"""Count and rank unmatched ingredient tokens across the product catalog."""

import argparse
import asyncio
import csv
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.modules.catalog.models import ProductIngredient
from app.modules.ingredients.normalizer import normalize

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = BACKEND_DIR.parent / "docs" / "reports" / "unmatched_ingredient_frequency.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank unmatched ingredient tokens across the product catalog."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to output CSV file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of ranked tokens to output.",
    )
    return parser.parse_args(argv)


async def generate_frequency_report(db: AsyncSession, output_path: Path, limit: int = 500) -> int:
    query = select(ProductIngredient.raw_text, ProductIngredient.product_id).where(
        ProductIngredient.ingredient_id.is_(None)
    )
    res = await db.execute(query)
    rows = res.all()

    occurrence_counts: Counter[str] = Counter()
    product_sets: dict[str, set[object]] = defaultdict(set)
    examples: dict[str, str] = {}

    for raw_text, product_id in rows:
        if not raw_text:
            continue
        norm = normalize(raw_text)
        if not norm:
            continue
        occurrence_counts[norm] += 1
        product_sets[norm].add(product_id)
        if norm not in examples:
            examples[norm] = raw_text

    ranked_tokens = occurrence_counts.most_common(limit)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["normalized_token", "occurrences", "product_count", "example_raw_text"])
        for token, count in ranked_tokens:
            writer.writerow([token, count, len(product_sets[token]), examples.get(token, "")])

    logger.info("Wrote %d unmatched tokens to %s", len(ranked_tokens), output_path)
    return len(ranked_tokens)


async def main() -> None:
    args = parse_args()
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with session_factory() as db:
        await generate_frequency_report(db, args.output, args.limit)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
