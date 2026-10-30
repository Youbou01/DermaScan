"""Integration tests for GET /api/v1/home and section load-more."""

from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.pagination import encode_cursor
from app.modules.catalog.models import Product
from tests.factories import make_brand, make_category, make_product
from tests.integration.helpers import freeze_home_feed_date

pytestmark = pytest.mark.usefixtures("migrated_database")

DAY_A = date(2026, 10, 19)
DAY_B = date(2026, 10, 20)


async def _add_scored_products(
    session: AsyncSession,
    *,
    count: int,
    score: int = 80,
    band: RiskLevel = RiskLevel.LOW,
    base_created: datetime | None = None,
) -> list[Product]:
    brand = make_brand()
    category = make_category(names={"en": "Moisturizer", "fr": "Hydratant"}, slug="moisturizer")
    session.add_all([brand, category])
    await session.flush()
    start = base_created or datetime(2026, 1, 1, tzinfo=UTC)
    products: list[Product] = []
    for i in range(count):
        product = make_product(
            name=f"Product {i}",
            brand_id=brand.id,
            primary_category_id=category.id,
            score=score,
            score_band=band,
            score_coverage=1.0,
            created_at=start + timedelta(minutes=i),
        )
        session.add(product)
        products.append(product)
    await session.flush()
    return products


async def test_home_feed_empty_database(client: httpx.AsyncClient) -> None:
    freeze_home_feed_date(client, DAY_A)
    response = await client.get("/api/v1/home")
    assert response.status_code == 200
    sections = {s["id"]: s for s in response.json()["sections"]}
    assert list(sections) == ["categories", "top_rated", "recently_added"]
    assert sections["categories"]["items"] == []
    assert sections["top_rated"]["items"] == []
    assert sections["recently_added"]["items"] == []
    assert sections["top_rated"]["next_cursor"] is None
    assert sections["categories"]["title"] == "Categories"
    assert response.headers["content-language"] == "en"


async def test_home_feed_french_titles_and_categories(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    parent = make_category(names={"en": "Face care", "fr": "Soin du visage"}, slug="face-care")
    db_session.add(parent)
    await db_session.flush()
    await _add_scored_products(db_session, count=1)

    response = await client.get("/api/v1/home", headers={"Accept-Language": "fr-TN"})
    body = response.json()
    sections = {s["id"]: s for s in body["sections"]}

    assert response.headers["content-language"] == "fr"
    assert sections["categories"]["title"] == "Catégories"
    assert sections["top_rated"]["title"] == "Mieux notés"
    assert sections["recently_added"]["title"] == "Ajoutés récemment"
    assert sections["categories"]["items"][0]["name"] == "Soin du visage"


async def test_home_feed_single_product_and_null_score_excluded_from_top_rated(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    brand = make_brand()
    db_session.add(brand)
    await db_session.flush()
    scored = make_product(name="Scored", brand_id=brand.id, score=90, score_band=RiskLevel.LOW)
    unscored = make_product(name="Unscored", brand_id=brand.id, score=None)
    insufficient = make_product(
        name="Insufficient", brand_id=brand.id, score=50, score_band=RiskLevel.UNKNOWN
    )
    db_session.add_all([scored, unscored, insufficient])
    await db_session.flush()

    body = (await client.get("/api/v1/home")).json()
    sections = {s["id"]: s for s in body["sections"]}
    top_names = [p["name"] for p in sections["top_rated"]["items"]]
    recent_names = [p["name"] for p in sections["recently_added"]["items"]]

    assert top_names == ["Scored"]
    assert set(recent_names) == {"Scored", "Unscored", "Insufficient"}


async def test_home_feed_pagination_walk_collects_each_product_once(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    products = await _add_scored_products(db_session, count=5)
    expected = {str(p.id) for p in products}

    first = (await client.get("/api/v1/home", params={"limit": 2})).json()
    top = {s["id"]: s for s in first["sections"]}["top_rated"]
    seen = [item["id"] for item in top["items"]]
    cursor = top["next_cursor"]
    assert cursor is not None
    assert len(seen) == 2

    while cursor is not None:
        page = (
            await client.get(
                "/api/v1/home/sections/top_rated",
                params={"cursor": cursor, "limit": 2},
            )
        ).json()
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]

    assert len(seen) == len(expected)
    assert set(seen) == expected


async def test_home_feed_last_page_has_null_cursor(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    await _add_scored_products(db_session, count=3)

    body = (await client.get("/api/v1/home", params={"limit": 10})).json()
    top = {s["id"]: s for s in body["sections"]}["top_rated"]
    assert len(top["items"]) == 3
    assert top["next_cursor"] is None


async def test_home_feed_exact_page_size_has_no_next_cursor(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    await _add_scored_products(db_session, count=4)

    body = (await client.get("/api/v1/home", params={"limit": 4})).json()
    top = {s["id"]: s for s in body["sections"]}["top_rated"]
    assert len(top["items"]) == 4
    assert top["next_cursor"] is None


async def test_home_feed_page_size_plus_one_has_next_cursor(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    await _add_scored_products(db_session, count=5)

    body = (await client.get("/api/v1/home", params={"limit": 4})).json()
    top = {s["id"]: s for s in body["sections"]}["top_rated"]
    assert len(top["items"]) == 4
    assert top["next_cursor"] is not None


async def test_recently_added_pagination_walk_no_duplicates(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    products = await _add_scored_products(db_session, count=5)
    expected = {str(p.id) for p in products}

    first = (await client.get("/api/v1/home", params={"limit": 2})).json()
    recent = {s["id"]: s for s in first["sections"]}["recently_added"]
    seen = [item["id"] for item in recent["items"]]
    cursor = recent["next_cursor"]
    assert cursor is not None

    while cursor is not None:
        page = (
            await client.get(
                "/api/v1/home/sections/recently_added",
                params={"cursor": cursor, "limit": 2},
            )
        ).json()
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]

    assert len(seen) == len(expected)
    assert set(seen) == expected


async def test_top_rated_order_stable_same_day_changes_next_day(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _add_scored_products(db_session, count=8, score=80)

    freeze_home_feed_date(client, DAY_A)
    order_a1 = [
        p["id"]
        for p in (await client.get("/api/v1/home", params={"limit": 8})).json()["sections"][1][
            "items"
        ]
    ]
    order_a2 = [
        p["id"]
        for p in (await client.get("/api/v1/home", params={"limit": 8})).json()["sections"][1][
            "items"
        ]
    ]
    freeze_home_feed_date(client, DAY_B)
    order_b = [
        p["id"]
        for p in (await client.get("/api/v1/home", params={"limit": 8})).json()["sections"][1][
            "items"
        ]
    ]

    assert order_a1 == order_a2
    assert set(order_a1) == set(order_b)
    assert order_a1 != order_b  # rotation changes with the date


async def test_cursor_from_day_n_still_paginates_on_day_n_plus_1(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _add_scored_products(db_session, count=5, score=70)
    freeze_home_feed_date(client, DAY_A)
    first = (await client.get("/api/v1/home", params={"limit": 2})).json()
    cursor = first["sections"][1]["next_cursor"]
    page1_ids = {p["id"] for p in first["sections"][1]["items"]}
    assert cursor is not None

    freeze_home_feed_date(client, DAY_B)
    second = (
        await client.get(
            "/api/v1/home/sections/top_rated",
            params={"cursor": cursor, "limit": 2},
        )
    ).json()
    page2_ids = {p["id"] for p in second["items"]}

    assert page1_ids.isdisjoint(page2_ids)


async def test_invalid_cursor_and_wrong_section_return_400_problem(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    freeze_home_feed_date(client, DAY_A)
    await _add_scored_products(db_session, count=1)

    garbage = await client.get("/api/v1/home/sections/top_rated", params={"cursor": "not-a-cursor"})
    assert garbage.status_code == 400
    assert garbage.headers["content-type"] == "application/problem+json"
    assert garbage.json()["type"] == "urn:skincare:problem:invalid-cursor"

    foreign = encode_cursor(
        {
            "s": "recently_added",
            "created_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            "id": "00000000-0000-7000-8000-000000000001",
        }
    )
    wrong = await client.get("/api/v1/home/sections/top_rated", params={"cursor": foreign})
    assert wrong.status_code == 400
    assert wrong.json()["type"] == "urn:skincare:problem:invalid-cursor"


@pytest.mark.parametrize("limit", [0, 51, -1])
async def test_limit_out_of_range_is_400(client: httpx.AsyncClient, limit: int) -> None:
    response = await client.get("/api/v1/home", params={"limit": limit})
    assert response.status_code == 400
    assert response.json()["type"] == "urn:skincare:problem:invalid-limit"


async def test_unknown_section_is_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/home/sections/not-a-section")
    assert response.status_code == 404
    assert response.json()["type"] == "urn:skincare:problem:section-not-found"


async def test_product_card_shape(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    freeze_home_feed_date(client, DAY_A)
    products = await _add_scored_products(db_session, count=1)
    product = products[0]

    card = (await client.get("/api/v1/home")).json()["sections"][1]["items"][0]
    assert set(card) == {
        "id",
        "name",
        "brand",
        "image_url",
        "score",
        "score_band",
        "score_is_estimated",
        "category_slug",
    }
    assert card["id"] == str(product.id)
    assert card["category_slug"] == "moisturizer"
    assert card["score"] == 80
    assert card["score_band"] == "low"
