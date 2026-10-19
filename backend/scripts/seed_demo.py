"""DEV ONLY: inserts a handful of demo ingredients and products so the API has something to show.

    uv run python scripts/seed_demo.py

It runs the real pipeline (label text -> parse -> match -> store), so it also shows how
B2-B4 fit together. It is safe to run twice. Real data will come from the ingredient seed
loader (task B5) and the Open Beauty Facts importer (task E2); this script goes away then.
Scores stay empty until the scoring module exists (task C1).
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.core.enums import RiskLevel
from app.modules.catalog.enums import ProductSource
from app.modules.catalog.gtin import compute_check_digit
from app.modules.catalog.models import (
    Brand,
    Category,
    CategoryTranslation,
    Product,
    ProductIngredient,
)
from app.modules.ingredients import IngredientService, normalize, parse_ingredient_label
from app.modules.ingredients.models import Ingredient, IngredientAlias, IngredientTranslation

# (INCI name, risk, extra names, {locale: rationale}, source)
INGREDIENTS: list[tuple[str, RiskLevel, list[str], dict[str, str], str | None]] = [
    ("AQUA", RiskLevel.LOW, ["Water", "Eau"], {}, None),
    ("GLYCERIN", RiskLevel.LOW, ["Glycerine", "Glycérine", "E422"], {}, None),
    ("CETEARYL ALCOHOL", RiskLevel.LOW, ["Alcool cétéarylique"], {}, None),
    ("TOCOPHEROL", RiskLevel.LOW, ["Vitamin E", "Vitamine E"], {}, None),
    ("CITRIC ACID", RiskLevel.LOW, ["Acide citrique", "E330"], {}, None),
    (
        "PARFUM",
        RiskLevel.MODERATE,
        ["Fragrance", "Parfum (Fragrance)"],
        {
            "en": "Undisclosed fragrance mixtures can contain allergens.",
            "fr": "Les parfums non détaillés peuvent contenir des allergènes.",
        },
        "Demo data (not a real assessment)",
    ),
    (
        "PROPYLPARABEN",
        RiskLevel.HIGH,
        ["Propyl paraben"],
        {"en": "Restricted preservative (demo text)."},
        "Demo data (not a real assessment)",
    ),
]

# (12-digit body, name, brand, label)
PRODUCTS: list[tuple[str, str, str, str]] = [
    (
        "619000000001",
        "Soft Day Cream",
        "Demo Brand",
        "Ingredients: Aqua (Water), Glycerin, Cetearyl Alcohol, Parfum (Fragrance), "
        "Tocopherol*, Citric Acid. +/- CI 77891",
    ),
    (
        "619000000002",
        "Crème Hydratante Douce",
        "Marque Démo",
        "Ingrédients : Eau, Glycérine, Alcool cétéarylique, Propylparaben, Extrait mystère",
    ),
    (
        "619000000003",
        "Mystery Serum",
        "Demo Brand",
        "Aqua, Rare Botanical Extract, Unknown Complex",
    ),
]


def unique_aliases(names: list[str]) -> dict[str, str]:
    """normalized key -> first spelling. "Glycerine" and "Glycérine" collapse to the same key,
    and the database (rightly) refuses two aliases with one key."""
    keys: dict[str, str] = {}
    for name in names:
        keys.setdefault(normalize(name), name)
    return keys


async def seed(session: AsyncSession) -> None:
    category = await session.scalar(select(Category).where(Category.slug == "moisturizer"))
    if category is None:
        category = Category(
            slug="moisturizer",
            translations=[
                CategoryTranslation(locale="en", name="Moisturizer"),
                CategoryTranslation(locale="fr", name="Hydratant"),
            ],
        )
        session.add(category)

    for inci, risk, extra_names, rationale, source in INGREDIENTS:
        if await session.scalar(select(Ingredient.id).where(Ingredient.inci_name == inci)):
            continue
        session.add(
            Ingredient(
                inci_name=inci,
                risk_level=risk,
                source_ref=source,
                aliases=[
                    IngredientAlias(alias=name, normalized_alias=key)
                    for key, name in unique_aliases([inci, *extra_names]).items()
                ],
                translations=[
                    IngredientTranslation(locale=loc, rationale=text)
                    for loc, text in rationale.items()
                ],
            )
        )
    await session.flush()

    ingredients = IngredientService(session)
    for body, name, brand_name, label in PRODUCTS:
        barcode = body + str(compute_check_digit(body))
        if await session.scalar(select(Product.id).where(Product.barcode == barcode)):
            continue
        brand = await session.scalar(select(Brand).where(Brand.name == brand_name))
        if brand is None:
            brand = Brand(name=brand_name)
            session.add(brand)
            await session.flush()

        parsed = parse_ingredient_label(label)  # B3
        matches = await ingredients.match([item.text for item in parsed])  # B4
        session.add(
            Product(
                barcode=barcode,
                name=name,
                brand_id=brand.id,
                primary_category_id=category.id,
                raw_ingredients_text=label,
                source=ProductSource.MANUAL,
                ingredients=[
                    ProductIngredient(
                        position=item.position, raw_text=item.text, ingredient_id=m.ingredient_id
                    )
                    for item, m in zip(parsed, matches, strict=True)
                ],
            )
        )
        print(f"{barcode}  {name}")  # noqa: T201
    await session.commit()


async def main() -> None:
    engine = create_engine(get_settings())
    async with create_session_factory(engine)() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
