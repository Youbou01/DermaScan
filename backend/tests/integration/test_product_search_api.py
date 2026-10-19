import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.models import Category, Product, ProductIngredient
from app.modules.ingredients.models import Ingredient
from tests.factories import make_category, make_ingredient, make_product

pytestmark = pytest.mark.usefixtures("migrated_database")

PRODUCTS = "/api/v1/products"


def item_ids(response: httpx.Response) -> list[str]:
    return [item["id"] for item in response.json()["items"]]


async def save(session: AsyncSession, *objects: object) -> None:
    session.add_all(objects)
    await session.flush()


async def add_scored(
    session: AsyncSession,
    category: Category,
    score: int | None,
    band: RiskLevel = RiskLevel.LOW,
    ingredient: Ingredient | None = None,
) -> Product:
    product = make_product(primary_category_id=category.id, score=score)
    if score is not None:
        product.score_band = band
    if ingredient is not None:
        product.ingredients = [
            ProductIngredient(
                position=1, raw_text=ingredient.inci_name, ingredient_id=ingredient.id
            )
        ]
    await save(session, product)
    return product


# ------------------------------------------------------------------------ /search
async def test_search_ignores_accents_and_case(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    product = make_product(name="Crème Hydratante Visage")
    await save(db_session, product)

    response = await client.get(f"{PRODUCTS}/search", params={"q": "CREME hydratante"})

    assert response.status_code == 200
    assert str(product.id) in item_ids(response)


async def test_search_tolerates_a_typo(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    product = make_product(name="Hydratante")
    await save(db_session, product)

    response = await client.get(f"{PRODUCTS}/search", params={"q": "hydratnte"})

    assert str(product.id) in item_ids(response)


async def test_search_puts_prefix_matches_first(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    prefix_match = make_product(name="Cera Gel")
    inner_match = make_product(name="Fresh Cera Cream")
    await save(db_session, inner_match, prefix_match)

    response = await client.get(f"{PRODUCTS}/search", params={"q": "cera"})

    ids = item_ids(response)
    assert ids.index(str(prefix_match.id)) < ids.index(str(inner_match.id))


async def test_search_with_only_punctuation_returns_an_empty_page(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(f"{PRODUCTS}/search", params={"q": "!!!"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


async def test_search_requires_q(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{PRODUCTS}/search")

    assert response.status_code == 422


async def test_search_pagination_walks_every_result_once(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    products = [make_product(name=f"Zeta Soap {n}") for n in range(3)]
    await save(db_session, *products)

    first = await client.get(f"{PRODUCTS}/search", params={"q": "zeta soap", "limit": 2})
    cursor = first.json()["next_cursor"]
    assert cursor is not None
    second = await client.get(
        f"{PRODUCTS}/search", params={"q": "zeta soap", "limit": 2, "cursor": cursor}
    )

    seen = item_ids(first) + item_ids(second)
    assert len(seen) == 3
    assert set(seen) == {str(p.id) for p in products}
    assert second.json()["next_cursor"] is None


async def test_search_rejects_a_garbage_cursor(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{PRODUCTS}/search", params={"q": "cream", "cursor": "abc"})

    assert response.status_code == 422


# ------------------------------------------------------------------------ /filter
async def test_filter_returns_scored_products_best_first(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    category = make_category()
    await save(db_session, category)
    low = await add_scored(db_session, category, 50)
    high = await add_scored(db_session, category, 90)
    unscored = await add_scored(db_session, category, None)

    response = await client.get(f"{PRODUCTS}/filter", params={"category": category.slug})

    assert response.status_code == 200
    assert item_ids(response) == [str(high.id), str(low.id)]
    assert str(unscored.id) not in item_ids(response)


async def test_filter_by_category_includes_child_categories(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    parent = make_category()
    await save(db_session, parent)
    child = make_category(parent_id=parent.id)
    await save(db_session, child)
    product = await add_scored(db_session, child, 70)

    response = await client.get(f"{PRODUCTS}/filter", params={"category": parent.slug})

    assert item_ids(response) == [str(product.id)]


async def test_filter_with_unknown_category_is_empty(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{PRODUCTS}/filter", params={"category": "no-such-category"})

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_filter_by_band(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    category = make_category()
    await save(db_session, category)
    safe = await add_scored(db_session, category, 85, RiskLevel.LOW)
    await add_scored(db_session, category, 20, RiskLevel.HIGH)

    response = await client.get(
        f"{PRODUCTS}/filter", params={"category": category.slug, "band": RiskLevel.LOW.value}
    )

    assert item_ids(response) == [str(safe.id)]


async def test_filter_by_score_range(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    category = make_category()
    await save(db_session, category)
    await add_scored(db_session, category, 30)
    middle = await add_scored(db_session, category, 60)
    await add_scored(db_session, category, 95)

    response = await client.get(
        f"{PRODUCTS}/filter",
        params={"category": category.slug, "min_score": 50, "max_score": 70},
    )

    assert item_ids(response) == [str(middle.id)]


async def test_filter_rejects_min_score_above_max_score(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{PRODUCTS}/filter", params={"min_score": 80, "max_score": 20})

    assert response.status_code == 422
    assert response.json()["type"].endswith("invalid-score-range")


async def test_filter_include_and_exclude_ingredient(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    category = make_category()
    niacinamide = make_ingredient(inci_name="NIACINAMIDE")
    await save(db_session, category, niacinamide)
    with_it = await add_scored(db_session, category, 80, ingredient=niacinamide)
    without_it = await add_scored(db_session, category, 70)

    included = await client.get(
        f"{PRODUCTS}/filter", params={"category": category.slug, "include": "niacinamide"}
    )
    excluded = await client.get(
        f"{PRODUCTS}/filter", params={"category": category.slug, "exclude": "niacinamide"}
    )

    assert item_ids(included) == [str(with_it.id)]
    assert item_ids(excluded) == [str(without_it.id)]


async def test_filter_include_unknown_ingredient_is_empty(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    category = make_category()
    await save(db_session, category)
    await add_scored(db_session, category, 80)

    response = await client.get(
        f"{PRODUCTS}/filter", params={"category": category.slug, "include": "zzqqxxvv"}
    )

    assert response.json()["items"] == []
