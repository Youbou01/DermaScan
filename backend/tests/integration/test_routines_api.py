"""Integration coverage for routine editing, conflicts, adherence, and recommendations."""

import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.core.security import create_access_token, hash_password
from app.modules.catalog.models import Category, Product, ProductIngredient
from app.modules.identity.models import UserAccount
from tests.factories import make_category, make_ingredient, make_product


async def _auth_headers(session: AsyncSession) -> dict[str, str]:
    user = UserAccount(
        email="routine-user@example.test",
        password_hash=hash_password("test-password"),
        display_name="Routine user",
    )
    session.add(user)
    await session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def _product(
    session: AsyncSession,
    *,
    name: str,
    category: Category,
    ingredient_id: uuid.UUID,
    ingredient_text: str,
    score: int,
) -> Product:
    product = make_product(
        name=name,
        primary_category_id=category.id,
        score=score,
        score_band=RiskLevel.LOW,
        score_coverage=1.0,
        score_is_estimated=False,
        score_dirty=False,
    )
    product.ingredients = [
        ProductIngredient(position=1, raw_text=ingredient_text, ingredient_id=ingredient_id)
    ]
    session.add(product)
    await session.flush()
    return product


async def test_routine_crud_conflicts_and_daily_completion(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    serum = make_category(slug="serum")
    toner = make_category(slug="toner")
    retinol = make_ingredient(inci_name="RETINOL", aliases=["Retinol"])
    glycolic = make_ingredient(inci_name="GLYCOLIC ACID", aliases=["Glycolic Acid"])
    db_session.add_all([serum, toner, retinol, glycolic])
    await db_session.flush()
    retinol_serum = await _product(
        db_session,
        name="Retinol Serum",
        category=serum,
        ingredient_id=retinol.id,
        ingredient_text="Retinol",
        score=84,
    )
    glycolic_toner = await _product(
        db_session,
        name="Glycolic Toner",
        category=toner,
        ingredient_id=glycolic.id,
        ingredient_text="Glycolic Acid",
        score=82,
    )
    headers = await _auth_headers(db_session)

    initial = await client.put(
        "/api/v1/routines/evening",
        headers=headers,
        json={
            "steps": [
                {
                    "step_order": 1,
                    "step_type": "serum",
                    "product_id": str(retinol_serum.id),
                }
            ]
        },
    )
    preflight = await client.post(
        f"/api/v1/routines/evening/check-conflict/{glycolic_toner.id}", headers=headers
    )
    updated = await client.put(
        "/api/v1/routines/evening",
        headers=headers,
        json={
            "steps": [
                {
                    "step_order": 1,
                    "step_type": "serum",
                    "product_id": str(retinol_serum.id),
                },
                {
                    "step_order": 2,
                    "step_type": "toner",
                    "product_id": str(glycolic_toner.id),
                },
            ]
        },
    )

    assert initial.status_code == preflight.status_code == updated.status_code == 200
    assert preflight.json()["has_conflict"] is True
    assert preflight.json()["conflicts"][0]["code"] == "retinoid_x_acid"
    assert updated.json()["conflicts"][0]["severity"] == "high"
    assert [step["step_order"] for step in updated.json()["steps"]] == [1, 2]

    completed = await client.post("/api/v1/routines/evening/complete", headers=headers)
    uncompleted = await client.post("/api/v1/routines/evening/complete", headers=headers)
    listed = await client.get("/api/v1/routines", headers=headers)

    assert completed.status_code == uncompleted.status_code == listed.status_code == 200
    assert completed.json()["completed_today"] is True
    assert uncompleted.json()["completed_today"] is False
    assert listed.json()["routines"][0]["slot"] == "evening"
    assert listed.json()["routines"][0]["conflicts"][0]["code"] == "retinoid_x_acid"


async def test_recommendations_are_complete_and_filter_unsuitable_candidates(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    cleanser_category = make_category(slug="cleanser")
    serum_category = make_category(slug="serum")
    moisturizer_category = make_category(slug="moisturizer")
    sunscreen_category = make_category(slug="sunscreen")
    glycerin = make_ingredient(inci_name="GLYCERIN", aliases=["Glycerin"])
    alcohol = make_ingredient(inci_name="ALCOHOL DENAT.", aliases=["Alcohol Denat."])
    db_session.add_all(
        [
            cleanser_category,
            serum_category,
            moisturizer_category,
            sunscreen_category,
            glycerin,
            alcohol,
        ]
    )
    await db_session.flush()
    await _product(
        db_session,
        name="Gentle Cleanser",
        category=cleanser_category,
        ingredient_id=glycerin.id,
        ingredient_text="Glycerin",
        score=90,
    )
    await _product(
        db_session,
        name="Alcohol Serum",
        category=serum_category,
        ingredient_id=alcohol.id,
        ingredient_text="Alcohol Denat.",
        score=99,
    )
    await _product(
        db_session,
        name="Hydrating Serum",
        category=serum_category,
        ingredient_id=glycerin.id,
        ingredient_text="Glycerin",
        score=88,
    )
    await _product(
        db_session,
        name="Barrier Cream",
        category=moisturizer_category,
        ingredient_id=glycerin.id,
        ingredient_text="Glycerin",
        score=87,
    )
    await _product(
        db_session,
        name="Daily Sunscreen",
        category=sunscreen_category,
        ingredient_id=glycerin.id,
        ingredient_text="Glycerin",
        score=86,
    )
    headers = await _auth_headers(db_session)

    response = await client.get("/api/v1/routines/recommendations?skin_type=dry", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["skin_type"] == "dry"
    assert [step["step_type"] for step in body["morning"]] == [
        "cleanser",
        "serum",
        "moisturizer",
        "sunscreen",
    ]
    assert [step["step_type"] for step in body["evening"]] == [
        "cleanser",
        "treatment",
        "moisturizer",
    ]
    recommended_names = {
        step["product"]["name"]
        for routine in (body["morning"], body["evening"])
        for step in routine
    }
    assert "Alcohol Serum" not in recommended_names


async def test_shared_routine_is_allowlisted_copy_requires_confirmation_and_can_be_revoked(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await _auth_headers(db_session)
    source_product = make_product(name="Shared moisturizer")
    existing_product = make_product(name="Recipient's old cleanser")
    db_session.add_all([source_product, existing_product])
    await db_session.flush()

    source = await client.put(
        "/api/v1/routines/morning",
        headers=owner_headers,
        json={
            "steps": [
                {
                    "step_order": 1,
                    "step_type": "moisturizer",
                    "product_id": str(source_product.id),
                    "notes": "private note that must not be shared",
                }
            ]
        },
    )
    assert source.status_code == 200

    created = await client.post(
        "/api/v1/routines/morning/share",
        headers=owner_headers,
        json={"expires_in_days": 7},
    )
    assert created.status_code == 201
    share = created.json()
    token = share["share_token"]

    public = await client.get(f"/api/v1/routines/shared/{token}")
    assert public.status_code == 200
    body = public.json()
    assert set(body) == {"slot", "expires_at", "steps"}
    assert body["slot"] == "morning"
    assert set(body["steps"][0]) == {
        "step_order",
        "step_type",
        "product",
        "active_ingredients",
    }
    assert "private note that must not be shared" not in public.text
    assert "routine-user@example.test" not in public.text
    assert "user_id" not in public.text
    assert "health_conditions" not in public.text

    recipient = UserAccount(
        email="routine-recipient@example.test",
        password_hash=hash_password("test-password"),
        display_name="Recipient",
    )
    db_session.add(recipient)
    await db_session.flush()
    recipient_headers = {"Authorization": f"Bearer {create_access_token(recipient.id)}"}
    previous = await client.put(
        "/api/v1/routines/evening",
        headers=recipient_headers,
        json={
            "steps": [
                {
                    "step_order": 1,
                    "step_type": "cleanser",
                    "product_id": str(existing_product.id),
                }
            ]
        },
    )
    assert previous.status_code == 200

    missing_confirmation = await client.post(
        f"/api/v1/routines/shared/{token}/copy",
        headers=recipient_headers,
        json={"destination_slot": "evening"},
    )
    assert missing_confirmation.status_code == 422

    copied = await client.post(
        f"/api/v1/routines/shared/{token}/copy",
        headers=recipient_headers,
        json={"destination_slot": "evening", "confirm_replace": True},
    )
    assert copied.status_code == 200
    copied_body = copied.json()
    assert copied_body["slot"] == "evening"
    assert [step["product"]["id"] for step in copied_body["steps"]] == [str(source_product.id)]
    assert copied_body["steps"][0]["notes"] is None

    links = await client.get("/api/v1/routines/morning/shares", headers=owner_headers)
    assert links.status_code == 200
    [link] = links.json()["links"]
    assert link["id"] == share["id"]
    assert link["view_count"] >= 2
    assert link["last_viewed_at"] is not None

    denied = await client.delete(
        f"/api/v1/routines/shares/{share['id']}", headers=recipient_headers
    )
    assert denied.status_code == 404
    revoked = await client.delete(f"/api/v1/routines/shares/{share['id']}", headers=owner_headers)
    assert revoked.status_code == 204
    assert (await client.get(f"/api/v1/routines/shared/{token}")).status_code == 404
