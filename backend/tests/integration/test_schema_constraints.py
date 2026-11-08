"""The database must reject bad data by itself, not only the Python code.

These tests protect the rules that live in the schema (see the migration and models).
If one fails after a model change, the change weakened an invariant: think before fixing.
"""

import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.models import (
    Product,
    ProductIngredient,
)
from app.modules.ingredients.models import Ingredient, IngredientAlias
from tests.factories import (
    make_barcode,
    make_brand,
    make_category,
    make_ingredient,
    make_product,
)

pytestmark = pytest.mark.usefixtures("migrated_database")


async def test_product_defaults_are_filled_in(db_session: AsyncSession) -> None:
    product = make_product()
    db_session.add(product)
    await db_session.flush()
    await db_session.refresh(product)

    assert product.id.version == 7
    assert product.score is None
    assert product.score_band is RiskLevel.UNKNOWN  # unscored never looks safe
    assert product.created_at is not None
    assert product.updated_at is not None


async def test_flagged_ingredient_requires_a_source(db_session: AsyncSession) -> None:
    db_session.add(Ingredient(inci_name="PROPYLPARABEN", risk_level=RiskLevel.HIGH))

    with pytest.raises(IntegrityError, match="flagged_requires_source"):
        await db_session.flush()


async def test_normalized_alias_is_globally_unique(db_session: AsyncSession) -> None:
    first = make_ingredient()
    second = make_ingredient()
    first.aliases = [IngredientAlias(alias="Aqua", normalized_alias="aqua")]
    second.aliases = [IngredientAlias(alias="AQUA", normalized_alias="aqua")]
    db_session.add_all([first, second])

    with pytest.raises(IntegrityError, match="uq_ingredient_alias_normalized_alias"):
        await db_session.flush()


async def test_brand_names_are_unique_ignoring_case(db_session: AsyncSession) -> None:
    db_session.add_all([make_brand(name="Nivea"), make_brand(name="NIVEA")])

    with pytest.raises(IntegrityError, match="uq_brand_name_lower"):
        await db_session.flush()


@pytest.mark.parametrize("barcode", ["619123456789", "61912345678AB", ""])
async def test_barcode_must_be_exactly_13_digits(db_session: AsyncSession, barcode: str) -> None:
    db_session.add(make_product(barcode=barcode))

    with pytest.raises(IntegrityError, match="ck_product_barcode_gtin13"):
        await db_session.flush()


async def test_barcode_longer_than_13_characters_is_rejected(db_session: AsyncSession) -> None:
    db_session.add(make_product(barcode="61912345678901"))

    with pytest.raises(DBAPIError):  # stopped by the VARCHAR(13) length itself
        await db_session.flush()


async def test_barcode_is_unique(db_session: AsyncSession) -> None:
    barcode = make_barcode()
    db_session.add_all([make_product(barcode=barcode), make_product(barcode=barcode)])

    with pytest.raises(IntegrityError, match="uq_product_barcode"):
        await db_session.flush()


async def test_same_source_id_cannot_be_imported_twice(db_session: AsyncSession) -> None:
    from app.modules.catalog.enums import ProductSource

    source = ProductSource.OPEN_BEAUTY_FACTS
    db_session.add_all(
        [
            make_product(source=source, source_id="abc"),
            make_product(source=source, source_id="abc"),
        ]
    )

    with pytest.raises(IntegrityError, match="uq_product_source_source_id"):
        await db_session.flush()


@pytest.mark.parametrize("score", [-1, 101])
async def test_score_must_be_between_0_and_100(db_session: AsyncSession, score: int) -> None:
    db_session.add(make_product(score=score))

    with pytest.raises(IntegrityError, match="ck_product_score_range"):
        await db_session.flush()


async def test_locale_must_be_two_lowercase_letters(db_session: AsyncSession) -> None:
    category = make_category(names={"FR": "Hydratant"})
    db_session.add(category)

    with pytest.raises(IntegrityError, match="locale_format"):
        await db_session.flush()


async def test_database_rejects_values_outside_the_enum_even_via_raw_sql(
    db_session: AsyncSession,
) -> None:
    db_session.add(make_ingredient(inci_name="GLYCERIN"))
    await db_session.flush()

    with pytest.raises(DBAPIError, match=r"ck_ingredient_(risk_level|rating_risk_level_sync)"):
        await db_session.execute(
            text("UPDATE ingredient SET risk_level = 'safe' WHERE inci_name = 'GLYCERIN'")
        )


async def test_ingredient_used_by_a_product_cannot_be_deleted(db_session: AsyncSession) -> None:
    ingredient = make_ingredient()
    db_session.add(ingredient)
    await db_session.flush()
    product = make_product(
        ingredients=[ProductIngredient(position=1, raw_text="x", ingredient_id=ingredient.id)]
    )
    db_session.add(product)
    await db_session.flush()

    with pytest.raises(DBAPIError, match="fk_product_ingredient_ingredient_id_ingredient"):
        await db_session.execute(
            text("DELETE FROM ingredient WHERE id = :id"), {"id": ingredient.id}
        )


async def test_deleting_a_product_removes_its_ingredient_rows(db_session: AsyncSession) -> None:
    product = make_product(
        ingredients=[
            ProductIngredient(position=1, raw_text="Aqua"),
            ProductIngredient(position=2, raw_text="Mystery extract"),
        ]
    )
    db_session.add(product)
    await db_session.flush()
    product_id: uuid.UUID = product.id

    await db_session.execute(text("DELETE FROM product WHERE id = :id"), {"id": product_id})

    # Count in SQL: session.get() would return the cached Python object instead.
    rows = select(func.count()).select_from(ProductIngredient)
    assert await db_session.scalar(rows.where(ProductIngredient.product_id == product_id)) == 0
    products = select(func.count()).select_from(Product).where(Product.id == product_id)
    assert await db_session.scalar(products) == 0
