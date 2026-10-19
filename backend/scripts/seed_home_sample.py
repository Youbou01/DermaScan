"""DEV ONLY: insert ~30 sample products for manual home-feed testing.

    uv run python scripts/seed_home_sample.py
    uv run python scripts/seed_home_sample.py --purge

Uses valid GTIN-13 barcodes (D3 check digit). Categories must already be seeded
(`uv run python scripts/seed_categories.py`). Safe to re-run: skips existing barcodes.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.core.enums import RiskLevel
from app.modules.catalog.enums import ProductSource
from app.modules.catalog.gtin import compute_check_digit
from app.modules.catalog.models import Brand, Category, Product
from app.modules.scoring.engine import GOOD_MIN_SCORE, MODERATE_MIN_SCORE, SCORING_VERSION

# 12-digit bodies; check digit appended at insert time. Prefix 619 = Tunisia.
SAMPLE_BODY_START = 619000100000
SAMPLE_COUNT = 30
SOURCE_ID_PREFIX = "home-sample-"


async def _category_ids(session: AsyncSession) -> dict[str, object]:
    rows = (await session.execute(select(Category.slug, Category.id))).all()
    return dict(rows)


async def seed(session: AsyncSession) -> int:
    categories = await _category_ids(session)
    if "moisturizer" not in categories:
        msg = "Categories missing. Run: uv run python scripts/seed_categories.py"
        raise SystemExit(msg)

    brand = await session.scalar(select(Brand).where(Brand.name == "Home Sample Brand"))
    if brand is None:
        brand = Brand(name="Home Sample Brand")
        session.add(brand)
        await session.flush()

    child_slugs = [
        "cleanser",
        "toner",
        "serum",
        "moisturizer",
        "sunscreen",
        "body-lotion",
        "lip-care",
    ]
    created = 0
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(SAMPLE_COUNT):
        body = str(SAMPLE_BODY_START + i)
        barcode = body + str(compute_check_digit(body))
        if await session.scalar(select(Product.id).where(Product.barcode == barcode)):
            continue
        slug = child_slugs[i % len(child_slugs)]
        # Mix: scored, unscored, and "insufficient data" (unknown band).
        if i % 7 == 0:
            score, band, coverage = None, RiskLevel.UNKNOWN, None
        elif i % 11 == 0:
            score, band, coverage = 40, RiskLevel.UNKNOWN, 0.2
        else:
            score = 55 + (i % 40)
            band = (
                RiskLevel.LOW
                if score >= GOOD_MIN_SCORE
                else RiskLevel.MODERATE
                if score >= MODERATE_MIN_SCORE
                else RiskLevel.HIGH
            )
            coverage = 0.85
        session.add(
            Product(
                barcode=barcode,
                name=f"Sample Product {i + 1:02d}",
                brand_id=brand.id,
                primary_category_id=categories[slug],
                image_url=f"https://example.test/sample/{i + 1}.jpg" if i % 3 else None,
                score=score,
                score_band=band,
                score_coverage=coverage,
                # Current version, or recompute_scores.py would treat these rows as stale
                # and re-score them from their (non-existent) ingredients.
                scoring_version=SCORING_VERSION if score is not None else None,
                source=ProductSource.MANUAL,
                source_id=f"{SOURCE_ID_PREFIX}{i + 1:02d}",
                created_at=base + timedelta(hours=i),
            )
        )
        created += 1
        print(f"{barcode}  Sample Product {i + 1:02d}  score={score}")  # noqa: T201
    await session.commit()
    return created


async def purge(session: AsyncSession) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(Product)
        .where(Product.source_id.like(f"{SOURCE_ID_PREFIX}%"))
    )
    await session.execute(delete(Product).where(Product.source_id.like(f"{SOURCE_ID_PREFIX}%")))
    await session.commit()
    return int(count or 0)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or purge home-feed sample products.")
    parser.add_argument(
        "--purge", action="store_true", help="Remove products created by this script."
    )
    args = parser.parse_args()
    engine = create_engine(get_settings())
    async with create_session_factory(engine)() as session:
        if args.purge:
            removed = await purge(session)
            print(f"Removed {removed} sample product(s).")  # noqa: T201
        else:
            created = await seed(session)
            print(f"Inserted {created} sample product(s).")  # noqa: T201
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
