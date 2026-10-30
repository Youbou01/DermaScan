from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog import CatalogService
from app.modules.catalog.models import ProductIngredient
from app.modules.ingredients.models import Ingredient, IngredientAlias
from app.modules.ingredients.normalizer import normalize
from tests.factories import make_barcode, make_product

pytestmark = pytest.mark.usefixtures("migrated_database")


async def test_adding_dictionary_entry_rematches_and_rescores_product(
    db_session: AsyncSession,
) -> None:
    # 1. Create 2 known ingredients
    aqua = Ingredient(
        inci_name="Aqua",
        risk_level=RiskLevel.LOW,
        rating=Decimal("9.5"),
        rating_confidence=Decimal("1.0"),
    )
    aqua.aliases = [IngredientAlias(alias="Aqua", normalized_alias="aqua")]

    glycerin = Ingredient(
        inci_name="Glycerin",
        risk_level=RiskLevel.LOW,
        rating=Decimal("9.5"),
        rating_confidence=Decimal("1.0"),
    )
    glycerin.aliases = [IngredientAlias(alias="Glycerin", normalized_alias="glycerin")]

    db_session.add_all([aqua, glycerin])
    await db_session.flush()

    # 2. Create product with 3 ingredients: 2 matched, 1 unmatched
    product = make_product(barcode=make_barcode())
    db_session.add(product)
    await db_session.flush()

    pi1 = ProductIngredient(
        product_id=product.id, position=1, raw_text="Aqua", ingredient_id=aqua.id
    )
    pi2 = ProductIngredient(
        product_id=product.id, position=2, raw_text="Glycerin", ingredient_id=glycerin.id
    )
    pi3 = ProductIngredient(
        product_id=product.id,
        position=3,
        raw_text="Centella Asiatica Leaf Extract",
        ingredient_id=None,
    )
    db_session.add_all([pi1, pi2, pi3])
    await db_session.flush()

    catalog_service = CatalogService(db_session)

    # 3. Rescore initially with unmatched 3rd ingredient
    initial_rescored = await catalog_service.recompute_dirty_scores()
    assert initial_rescored == 1

    await db_session.refresh(product)
    initial_score = product.score
    initial_coverage = product.score_coverage
    assert product.score_dirty is False
    assert initial_coverage is not None
    assert initial_coverage < 1.0  # because item 3 is unmatched

    # 4. Add new dictionary entry for the unmatched ingredient
    centella = Ingredient(
        inci_name="Centella Asiatica Leaf Extract",
        risk_level=RiskLevel.LOW,
        rating=Decimal("9.5"),
        rating_confidence=Decimal("1.0"),
    )
    centella.aliases = [
        IngredientAlias(
            alias="Centella Asiatica Leaf Extract",
            normalized_alias=normalize("Centella Asiatica Leaf Extract"),
        )
    ]
    db_session.add(centella)
    await db_session.flush()

    # 5. Run rematch_unmatched
    rematched_count = await catalog_service.rematch_unmatched()
    assert rematched_count == 1

    # Product should now be marked dirty and pi3 should have ingredient_id
    await db_session.refresh(product)
    assert product.score_dirty is True

    await db_session.refresh(pi3)
    assert pi3.ingredient_id == centella.id

    # 6. Run recompute_dirty_scores
    rescored_count = await catalog_service.recompute_dirty_scores()
    assert rescored_count == 1

    await db_session.refresh(product)
    assert product.score_dirty is False
    assert product.score is not None
    assert product.score_coverage == 1.000
    assert product.score >= (initial_score or 0)
