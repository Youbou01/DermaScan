import asyncio
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.core.enums import RiskLevel
from app.modules.catalog.models import Product
from app.modules.ingredients.models import Ingredient
from app.modules.scoring import (
    SCORING_VERSION,
    IngredientPositionInput,
    calculate_score,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def recompute_stale_products(db: AsyncSession, batch_size: int = 100) -> int:
    """Finds products with missing or outdated scoring_version and updates them."""
    stmt = (
        select(Product)
        .options(selectinload(Product.ingredients))
        .where((Product.scoring_version.is_(None)) | (Product.scoring_version < SCORING_VERSION))
        .limit(batch_size)
    )
    result = await db.execute(stmt)
    stale_products = result.scalars().all()

    if not stale_products:
        return 0

    updated_count = 0
    for product in stale_products:
        input_items: list[IngredientPositionInput] = []
        for pi in product.ingredients:
            risk = RiskLevel.UNKNOWN
            if pi.ingredient_id is not None:
                ing_res = await db.execute(
                    select(Ingredient).where(Ingredient.id == pi.ingredient_id)
                )
                ing = ing_res.scalar_one_or_none()
                if ing is not None:
                    risk = RiskLevel(ing.risk_level.value)

            input_items.append(IngredientPositionInput(risk_level=risk, position=pi.position))

        score_output = calculate_score(input_items)

        product.score = score_output.score
        product.score_band = score_output.band
        product.score_coverage = score_output.coverage
        product.scoring_version = score_output.scoring_version
        updated_count += 1

    await db.commit()
    logger.info(
        "Recomputed scores for %d products (version %d).",
        updated_count,
        SCORING_VERSION,
    )
    return updated_count


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
