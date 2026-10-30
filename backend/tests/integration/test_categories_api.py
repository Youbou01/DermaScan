"""Integration tests for GET /api/v1/categories and the category seed loader."""

from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category, CategoryTranslation
from app.modules.ingestion.seed_categories import DATA_FILE, seed_categories
from tests.factories import make_category

pytestmark = pytest.mark.usefixtures("migrated_database")


async def test_category_tree_english_and_french(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    parent = make_category(names={"en": "Face care", "fr": "Soin du visage"}, slug="face-care")
    db_session.add(parent)
    await db_session.flush()
    child = make_category(
        names={"en": "Cleanser", "fr": "Nettoyant"}, slug="cleanser", parent_id=parent.id
    )
    db_session.add(child)
    await db_session.flush()

    en = await client.get("/api/v1/categories")
    fr = await client.get("/api/v1/categories", headers={"Accept-Language": "fr"})
    fr_tn = await client.get("/api/v1/categories", headers={"Accept-Language": "fr-TN"})
    de = await client.get("/api/v1/categories", headers={"Accept-Language": "de"})

    assert en.status_code == fr.status_code == 200
    assert en.json()[0]["slug"] == "face-care"
    assert en.json()[0]["name"] == "Face care"
    assert en.json()[0]["children"][0] == {"slug": "cleanser", "name": "Cleanser", "children": []}
    assert fr.json()[0]["name"] == "Soin du visage"
    assert fr.json()[0]["children"][0]["name"] == "Nettoyant"
    assert fr_tn.json()[0]["name"] == "Soin du visage"
    assert de.json()[0]["name"] == "Face care"
    assert fr.headers["content-language"] == "fr"
    assert "accept-language" in fr.headers["vary"].lower()
    assert en.headers["content-language"] == "en"


async def test_category_missing_french_falls_back_to_english(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add(make_category(names={"en": "Lip care"}, slug="lip-care"))
    await db_session.flush()

    body = (await client.get("/api/v1/categories", headers={"Accept-Language": "fr"})).json()

    assert body[0] == {"slug": "lip-care", "name": "Lip care", "children": []}


async def test_empty_categories_returns_empty_list(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.json() == []


async def test_seed_categories_is_idempotent(db_session: AsyncSession) -> None:
    assert DATA_FILE.is_file()
    first = await seed_categories(db_session, Path(DATA_FILE), commit=False)
    cats_1 = await db_session.scalar(select(func.count()).select_from(Category))
    tr_1 = await db_session.scalar(select(func.count()).select_from(CategoryTranslation))

    second = await seed_categories(db_session, Path(DATA_FILE), commit=False)
    cats_2 = await db_session.scalar(select(func.count()).select_from(Category))
    tr_2 = await db_session.scalar(select(func.count()).select_from(CategoryTranslation))

    assert first > 0
    assert second == 0
    assert cats_1 == cats_2 == 19
    assert tr_1 == tr_2 == 38


async def test_seeded_tree_structure_via_api(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await seed_categories(db_session, commit=False)

    body = (await client.get("/api/v1/categories", headers={"Accept-Language": "fr"})).json()
    by_slug = {node["slug"]: node for node in body}

    assert set(by_slug) == {"body-care", "face-care", "lip-care", "sun-care"}
    face = by_slug["face-care"]
    assert face["name"] == "Soin du visage"
    assert {c["slug"] for c in face["children"]} == {
        "cleanser",
        "toner",
        "serum",
        "moisturizer",
        "face-mask",
        "exfoliant",
        "eye-care",
    }
    assert by_slug["lip-care"]["children"] == []
