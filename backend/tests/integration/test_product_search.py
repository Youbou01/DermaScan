import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_product

pytestmark = pytest.mark.usefixtures("migrated_database")

URL = "/api/v1/products/search"


async def add_named(session: AsyncSession, *names: str) -> list[str]:
    """Persist one product per name and return their ids (as strings), in the same order."""
    products = [make_product(name=name) for name in names]
    session.add_all(products)
    await session.flush()
    return [str(product.id) for product in products]


def ids(response: httpx.Response) -> list[str]:
    return [item["id"] for item in response.json()["items"]]


async def test_search_ignores_accents_and_case(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    (cream_id,) = await add_named(db_session, "Crème Hydratante")

    for query in ("creme", "CRÈME", "crème hydr"):
        response = await client.get(URL, params={"q": query})
        assert response.status_code == 200
        assert cream_id in ids(response), query


async def test_prefix_match_ranks_before_fuzzy_match(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    fuzzy_id, prefix_id = await add_named(db_session, "Gel Cerave", "Cerave Gel")

    response = await client.get(URL, params={"q": "cerave"})

    assert response.status_code == 200
    found = ids(response)
    assert found.index(prefix_id) < found.index(fuzzy_id)


async def test_search_tolerates_a_typo(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    (product_id,) = await add_named(db_session, "Hydratante")

    response = await client.get(URL, params={"q": "hidratante"})

    assert product_id in ids(response)


async def test_unrelated_query_returns_an_empty_page(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await add_named(db_session, "Crème Hydratante")

    response = await client.get(URL, params={"q": "zzzzqqqq"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


async def test_punctuation_only_query_returns_an_empty_page(client: httpx.AsyncClient) -> None:
    response = await client.get(URL, params={"q": "!!!"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


async def test_search_pages_do_not_overlap(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    created = await add_named(db_session, "Pagetest A", "Pagetest B", "Pagetest C")

    first = await client.get(URL, params={"q": "pagetest", "limit": 2})
    assert first.status_code == 200
    assert len(first.json()["items"]) == 2
    cursor = first.json()["next_cursor"]
    assert cursor is not None

    second = await client.get(URL, params={"q": "pagetest", "limit": 2, "cursor": cursor})
    assert second.status_code == 200
    assert len(second.json()["items"]) == 1
    assert second.json()["next_cursor"] is None

    assert set(ids(first)) | set(ids(second)) == set(created)
    assert not set(ids(first)) & set(ids(second))


async def test_invalid_cursor_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get(URL, params={"q": "cream", "cursor": "not-a-number"})

    assert response.status_code == 422
    assert response.json()["type"].endswith("invalid-cursor")


async def test_search_requires_a_query(client: httpx.AsyncClient) -> None:
    response = await client.get(URL)

    assert response.status_code == 422
