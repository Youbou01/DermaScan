import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.models import Product, ProductIngredient
from app.modules.ingredients.models import Ingredient
from tests.factories import make_category, make_ingredient, make_product

pytestmark = pytest.mark.usefixtures("migrated_database")

URL = "/api/v1/products/filter"


async def add_scored(
    session: AsyncSession,
    score: int | None,
    band: RiskLevel = RiskLevel.LOW,
    ingredients: list[Ingredient] | None = None,
    **overrides: object,
) -> Product:
    """Persist a product with a score (None = not scored) and optional label ingredients."""
    if score is not None:
        overrides.update(score=score, score_band=band)
    product = make_product(**overrides)
    product.ingredients = [
        ProductIngredient(
            position=position, raw_text=ingredient.inci_name, ingredient_id=ingredient.id
        )
        for position, ingredient in enumerate(ingredients or [], start=1)
    ]
    session.add(product)
    await session.flush()
    return product


async def add_ingredient(session: AsyncSession, inci_name: str) -> Ingredient:
    ingredient = make_ingredient(inci_name=inci_name)
    session.add(ingredient)
    await session.flush()
    return ingredient


def ids(response: httpx.Response) -> list[str]:
    return [item["id"] for item in response.json()["items"]]


async def test_only_scored_products_best_score_first(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    low = await add_scored(db_session, 40, RiskLevel.MODERATE)
    high = await add_scored(db_session, 90)
    unscored = await add_scored(db_session, None)

    response = await client.get(URL)

    assert response.status_code == 200
    found = ids(response)
    assert str(unscored.id) not in found
    assert found.index(str(high.id)) < found.index(str(low.id))


async def test_score_range_is_inclusive(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    low = await add_scored(db_session, 50, RiskLevel.MODERATE)
    middle = await add_scored(db_session, 70)
    high = await add_scored(db_session, 90)

    response = await client.get(URL, params={"min_score": 60, "max_score": 80})

    found = ids(response)
    assert str(middle.id) in found
    assert str(low.id) not in found
    assert str(high.id) not in found


async def test_filter_by_band(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    good = await add_scored(db_session, 85, RiskLevel.LOW)
    bad = await add_scored(db_session, 20, RiskLevel.HIGH)

    response = await client.get(URL, params={"band": RiskLevel.HIGH.value})

    found = ids(response)
    assert str(bad.id) in found
    assert str(good.id) not in found


async def test_category_filter_includes_child_categories(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    parent = make_category(slug="filter-parent")
    other = make_category(slug="filter-other")
    db_session.add_all([parent, other])
    await db_session.flush()
    child = make_category(slug="filter-child", parent_id=parent.id)
    db_session.add(child)
    await db_session.flush()

    in_parent = await add_scored(db_session, 80, primary_category_id=parent.id)
    in_child = await add_scored(db_session, 70, primary_category_id=child.id)
    elsewhere = await add_scored(db_session, 60, primary_category_id=other.id)

    response = await client.get(URL, params={"category": "filter-parent"})

    found = ids(response)
    assert str(in_parent.id) in found
    assert str(in_child.id) in found
    assert str(elsewhere.id) not in found


async def test_unknown_category_gives_an_empty_page(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await add_scored(db_session, 80)

    response = await client.get(URL, params={"category": "no-such-category"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


async def test_include_requires_the_ingredient(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    glycerin = await add_ingredient(db_session, "TESTIUM GLYCERIN")
    with_it = await add_scored(db_session, 80, ingredients=[glycerin])
    without_it = await add_scored(db_session, 75)

    response = await client.get(URL, params={"include": "testium glycerin"})

    found = ids(response)
    assert str(with_it.id) in found
    assert str(without_it.id) not in found


async def test_include_needs_all_ingredients(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    alpha = await add_ingredient(db_session, "TESTIUM ALPHA")
    beta = await add_ingredient(db_session, "TESTIUM BETA")
    both = await add_scored(db_session, 80, ingredients=[alpha, beta])
    only_alpha = await add_scored(db_session, 75, ingredients=[alpha])

    response = await client.get(URL, params={"include": ["testium alpha", "testium beta"]})

    found = ids(response)
    assert str(both.id) in found
    assert str(only_alpha.id) not in found


async def test_unknown_include_name_gives_an_empty_page(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await add_scored(db_session, 80)

    response = await client.get(URL, params={"include": "no such ingredient"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


async def test_exclude_removes_products_with_the_ingredient(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    paraben = await add_ingredient(db_session, "TESTIUM PARABEN")
    with_it = await add_scored(db_session, 80, ingredients=[paraben])
    without_it = await add_scored(db_session, 75)

    response = await client.get(URL, params={"exclude": "testium paraben"})

    found = ids(response)
    assert str(without_it.id) in found
    assert str(with_it.id) not in found


async def test_unknown_exclude_name_is_ignored(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_scored(db_session, 80)

    response = await client.get(URL, params={"exclude": "no such ingredient"})

    assert response.status_code == 200
    assert str(product.id) in ids(response)


async def test_inverted_score_range_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get(URL, params={"min_score": 80, "max_score": 20})

    assert response.status_code == 422
    assert response.json()["type"].endswith("invalid-score-range")


async def test_score_pages_do_not_overlap_and_stay_ordered(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    created = [await add_scored(db_session, score) for score in (95, 85, 75)]
    expected = [str(p.id) for p in created]  # already best score first

    first = await client.get(URL, params={"min_score": 70, "limit": 2})
    cursor = first.json()["next_cursor"]
    assert cursor is not None
    second = await client.get(URL, params={"min_score": 70, "limit": 2, "cursor": cursor})

    assert ids(first) + ids(second) == expected
    assert second.json()["next_cursor"] is None
