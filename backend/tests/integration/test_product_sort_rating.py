"""Integration tests for sort=score|rating and direction=desc|asc null-last cursor pagination (US-31, US-33)."""

from decimal import Decimal

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.pagination import encode_cursor
from app.modules.catalog.models import Product, ProductIngredient
from tests.factories import make_brand, make_category, make_ingredient, make_product

pytestmark = pytest.mark.usefixtures("migrated_database")

URL = "/api/v1/products/filter"


async def _add_product(
    session: AsyncSession,
    *,
    name: str,
    score: int | None = 80,
    avg_rating: Decimal | None = None,
    band: RiskLevel = RiskLevel.LOW,
    category_id: object | None = None,
    brand_id: object | None = None,
    ingredients: list[object] | None = None,
) -> Product:
    product = make_product(
        name=name,
        score=score,
        score_band=band,
        score_coverage=1.0,
        score_is_estimated=False,
        score_dirty=False,
        avg_rating=avg_rating,
        review_count=1 if avg_rating is not None else 0,
        primary_category_id=category_id,
        brand_id=brand_id,
    )
    if ingredients:
        product.ingredients = [
            ProductIngredient(position=idx, raw_text=ing.inci_name, ingredient_id=ing.id)  # type: ignore[attr-defined]
            for idx, ing in enumerate(ingredients, start=1)
        ]
    session.add(product)
    await session.flush()
    return product


async def test_default_sort_is_score_desc(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    p_low = await _add_product(db_session, name="Low Score", score=30, band=RiskLevel.HIGH)
    p_mid = await _add_product(db_session, name="Mid Score", score=60, band=RiskLevel.MODERATE)
    p_high = await _add_product(db_session, name="High Score", score=90, band=RiskLevel.LOW)

    resp = await client.get(URL)
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids.index(str(p_high.id)) < ids.index(str(p_mid.id)) < ids.index(str(p_low.id))


async def test_sort_score_asc(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    p_low = await _add_product(db_session, name="Low Score", score=25, band=RiskLevel.HIGH)
    p_mid = await _add_product(db_session, name="Mid Score", score=55, band=RiskLevel.MODERATE)
    p_high = await _add_product(db_session, name="High Score", score=85, band=RiskLevel.LOW)

    resp = await client.get(f"{URL}?sort=score&direction=asc")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids.index(str(p_low.id)) < ids.index(str(p_mid.id)) < ids.index(str(p_high.id))


async def test_sort_rating_desc_nulls_last(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    p_r5 = await _add_product(db_session, name="Rating 5", avg_rating=Decimal("5.00"))
    p_r3 = await _add_product(db_session, name="Rating 3", avg_rating=Decimal("3.00"))
    p_r4 = await _add_product(db_session, name="Rating 4", avg_rating=Decimal("4.00"))
    p_unrated = await _add_product(db_session, name="Unrated", avg_rating=None)

    resp = await client.get(f"{URL}?sort=rating&direction=desc")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = [item["id"] for item in items]

    assert ids.index(str(p_r5.id)) < ids.index(str(p_r4.id)) < ids.index(str(p_r3.id))
    # Unrated must be after all rated
    assert ids.index(str(p_r3.id)) < ids.index(str(p_unrated.id))


async def test_sort_rating_asc_nulls_still_last(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    p_r5 = await _add_product(db_session, name="Rating 5", avg_rating=Decimal("5.00"))
    p_r2 = await _add_product(db_session, name="Rating 2", avg_rating=Decimal("2.00"))
    p_r4 = await _add_product(db_session, name="Rating 4", avg_rating=Decimal("4.00"))
    p_unrated = await _add_product(db_session, name="Unrated", avg_rating=None)

    resp = await client.get(f"{URL}?sort=rating&direction=asc")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = [item["id"] for item in items]

    assert ids.index(str(p_r2.id)) < ids.index(str(p_r4.id)) < ids.index(str(p_r5.id))
    # Unrated must STILL be at the end in asc direction!
    assert ids.index(str(p_r5.id)) < ids.index(str(p_unrated.id))


async def test_cursor_pagination_across_rated_unrated_boundary(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    r1 = await _add_product(db_session, name="P R5", avg_rating=Decimal("5.00"))
    r2 = await _add_product(db_session, name="P R4", avg_rating=Decimal("4.00"))
    r3 = await _add_product(db_session, name="P R3", avg_rating=Decimal("3.00"))
    u1 = await _add_product(db_session, name="P U1", avg_rating=None)
    u2 = await _add_product(db_session, name="P U2", avg_rating=None)
    all_expected = {str(r1.id), str(r2.id), str(r3.id), str(u1.id), str(u2.id)}

    # Test DESC direction across 3 pages with limit=2
    collected_desc: list[str] = []
    cursor: str | None = None
    while True:
        url = f"{URL}?sort=rating&direction=desc&limit=2"
        if cursor:
            url += f"&cursor={cursor}"
        resp = await client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            if item["id"] in all_expected:
                collected_desc.append(item["id"])
        cursor = data.get("next_cursor")
        if not cursor or len(collected_desc) >= 5:
            break

    assert len(collected_desc) == 5
    assert len(set(collected_desc)) == 5
    assert collected_desc[:3] == [str(r1.id), str(r2.id), str(r3.id)]

    # Test ASC direction across 3 pages with limit=2
    collected_asc: list[str] = []
    cursor = None
    while True:
        url = f"{URL}?sort=rating&direction=asc&limit=2"
        if cursor:
            url += f"&cursor={cursor}"
        resp = await client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            if item["id"] in all_expected:
                collected_asc.append(item["id"])
        cursor = data.get("next_cursor")
        if not cursor or len(collected_asc) >= 5:
            break

    assert len(collected_asc) == 5
    assert len(set(collected_asc)) == 5
    assert collected_asc[:3] == [str(r3.id), str(r2.id), str(r1.id)]


async def test_mismatched_sort_cursor_returns_422(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    p = await _add_product(db_session, name="Product")
    score_cursor = encode_cursor({"s": "score:desc", "v": "80", "id": str(p.id)})

    resp = await client.get(f"{URL}?sort=rating&direction=desc&cursor={score_cursor}")
    assert resp.status_code == 422
    assert resp.json()["type"] == "urn:skincare:problem:invalid-cursor"


async def test_combine_all_filters_with_sort_rating(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    cat = make_category(slug="face-cream")
    brand = make_brand(name="Bioderma")
    ing_inc = make_ingredient(inci_name="GLYCERIN", aliases=["Glycerin"])
    ing_exc = make_ingredient(inci_name="PARABEN", aliases=["Paraben"])
    db_session.add_all([cat, brand, ing_inc, ing_exc])
    await db_session.flush()

    # Matching product
    p_match = await _add_product(
        db_session,
        name="Sensibio Cream",
        score=75,
        avg_rating=Decimal("4.80"),
        band=RiskLevel.LOW,
        category_id=cat.id,
        brand_id=brand.id,
        ingredients=[ing_inc],
    )
    # Non-matching product (has excluded ingredient)
    p_non_match = await _add_product(
        db_session,
        name="Sensibio Rich",
        score=75,
        avg_rating=Decimal("4.90"),
        band=RiskLevel.LOW,
        category_id=cat.id,
        brand_id=brand.id,
        ingredients=[ing_inc, ing_exc],
    )

    query = (
        f"{URL}?q=Sensibio"
        f"&category=face-cream"
        f"&band=low"
        f"&min_score=50"
        f"&max_score=80"
        f"&include=Glycerin"
        f"&exclude=Paraben"
        f"&sort=rating"
        f"&direction=desc"
    )
    resp = await client.get(query)
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = [item["id"] for item in items]
    assert str(p_match.id) in ids
    assert str(p_non_match.id) not in ids
