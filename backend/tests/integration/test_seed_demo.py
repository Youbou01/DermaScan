from scripts.seed_demo import PRODUCTS, seed
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.models import Product
from app.modules.ingredients.models import Ingredient
from tests.factories import make_ingredient


async def test_demo_seed_reuses_curated_ingredients_and_is_idempotent(
    db_session: AsyncSession,
) -> None:
    aqua = make_ingredient(
        inci_name="Aqua",
        aliases=["Water", "Eau"],
        risk_level=RiskLevel.LOW,
    )
    db_session.add(aqua)
    await db_session.flush()

    await seed(db_session)
    await seed(db_session)

    aqua_count = await db_session.scalar(
        select(func.count(Ingredient.id)).where(func.lower(Ingredient.inci_name) == "aqua")
    )
    assert aqua_count == 1

    product_count = await db_session.scalar(select(func.count()).select_from(Product))
    assert product_count == len(PRODUCTS)
