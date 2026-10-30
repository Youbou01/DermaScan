from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.enums import ProductSource
from app.modules.catalog.models import Brand, Category, Product, ProductIngredient
from app.modules.ingredients.enums import RatingSource
from app.modules.ingredients.models import Ingredient
from app.modules.ingredients.service import IngredientService


@pytest.mark.asyncio
async def test_set_rating_updates_rating_and_derives_risk(db_session: AsyncSession) -> None:
    ing = Ingredient(
        inci_name="Test Ingredient A",
        rating_source=RatingSource.UNRATED,
    )
    db_session.add(ing)
    await db_session.flush()

    service = IngredientService(db_session)

    # 1. Low risk rating >= 7.0
    ok = await service.set_rating(
        ingredient_id=ing.id,
        rating=9.2,
        confidence=0.95,
        source=RatingSource.AI,
        model="gemini-1.5-flash",
    )
    assert ok is True
    assert ing.rating == Decimal("9.2")
    assert ing.risk_level == RiskLevel.LOW
    assert ing.rating_source == RatingSource.AI
    assert ing.rating_confidence == Decimal("0.95")
    assert ing.rating_model == "gemini-1.5-flash"


@pytest.mark.asyncio
async def test_set_rating_flagged_requires_source(db_session: AsyncSession) -> None:
    ing = Ingredient(
        inci_name="Test Irritant",
        rating_source=RatingSource.UNRATED,
    )
    db_session.add(ing)
    await db_session.flush()

    service = IngredientService(db_session)

    # Rating 5.5 is moderate concern -> requires source_ref, service auto-supplies if missing
    ok = await service.set_rating(
        ingredient_id=ing.id,
        rating=5.5,
        confidence=0.8,
        source=RatingSource.AI,
        model="qwen2.5:7b-instruct",
    )
    assert ok is True
    assert ing.rating == Decimal("5.5")
    assert ing.risk_level == RiskLevel.MODERATE
    assert ing.source_ref is not None
    assert "ai:" in ing.source_ref


@pytest.mark.asyncio
async def test_set_rating_never_overwrites_curated(db_session: AsyncSession) -> None:
    ing = Ingredient(
        inci_name="Test Curated Retinol",
        rating=Decimal("5.5"),
        risk_level=RiskLevel.MODERATE,
        source_ref="Expert Pharmacist Review",
        rating_source=RatingSource.CURATED,
    )
    db_session.add(ing)
    await db_session.flush()

    service = IngredientService(db_session)

    # AI attempt to overwrite curated rating is rejected
    ok = await service.set_rating(
        ingredient_id=ing.id,
        rating=8.0,
        source=RatingSource.AI,
    )
    assert ok is False
    assert ing.rating == Decimal("5.5")
    assert ing.rating_source == RatingSource.CURATED


@pytest.mark.asyncio
async def test_set_rating_regulatory_pre_rule_override(db_session: AsyncSession) -> None:
    prohibited_ing = Ingredient(
        inci_name="Prohibited Hydroquinone",
        is_prohibited=True,
        rating_source=RatingSource.UNRATED,
    )
    restricted_ing = Ingredient(
        inci_name="Restricted Preservative",
        is_restricted=True,
        rating_source=RatingSource.UNRATED,
    )
    db_session.add_all([prohibited_ing, restricted_ing])
    await db_session.flush()

    service = IngredientService(db_session)

    # Prohibited is forced to 0.5 regulatory regardless of input rating
    ok1 = await service.set_rating(
        ingredient_id=prohibited_ing.id,
        rating=9.9,
        source=RatingSource.AI,
    )
    assert ok1 is True
    assert prohibited_ing.rating == Decimal("0.5")
    assert prohibited_ing.risk_level == RiskLevel.HIGH
    assert prohibited_ing.rating_source == RatingSource.REGULATORY

    # Restricted is capped at 8.0
    ok2 = await service.set_rating(
        ingredient_id=restricted_ing.id,
        rating=9.5,
        source=RatingSource.AI,
    )
    assert ok2 is True
    assert restricted_ing.rating == Decimal("8.0")


@pytest.mark.asyncio
async def test_set_rating_marks_dependent_products_dirty(db_session: AsyncSession) -> None:
    brand = Brand(name="DermaCorp")
    category = Category(slug="serum")
    db_session.add_all([brand, category])
    await db_session.flush()

    prod = Product(
        name="Anti-Aging Serum",
        barcode="1234567890123",
        brand_id=brand.id,
        primary_category_id=category.id,
        score_dirty=False,
        source=ProductSource.OPEN_BEAUTY_FACTS,
        source_id="1234567890123",
    )
    ing = Ingredient(
        inci_name="Hyaluronic Acid",
        rating=Decimal("9.0"),
        risk_level=RiskLevel.LOW,
        rating_source=RatingSource.CURATED,
    )
    db_session.add_all([prod, ing])
    await db_session.flush()

    db_session.add(
        ProductIngredient(
            product_id=prod.id,
            ingredient_id=ing.id,
            raw_text="Hyaluronic Acid",
            position=1,
        )
    )
    await db_session.flush()
    assert prod.score_dirty is False

    service = IngredientService(db_session)

    # Calling set_rating marks prod.score_dirty = True via registered dirty hook
    ok = await service.set_rating(
        ingredient_id=ing.id,
        rating=9.5,
        source=RatingSource.CURATED,
        mark_dirty=True,
    )
    assert ok is True
    await db_session.refresh(prod)
    assert prod.score_dirty is True
