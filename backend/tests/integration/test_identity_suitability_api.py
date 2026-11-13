"""Integration tests for GET /api/v1/products/{product_id}/suitability."""

import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import ProductIngredient
from tests.factories import make_ingredient, make_product
from tests.integration.test_identity_api import BLACKLIST_URL, PROFILE_URL, _signed_in

pytestmark = pytest.mark.usefixtures("migrated_database")

RESPONSE_KEYS = {
    "product_id",
    "suits_profile",
    "verdict",
    "has_risk_alert",
    "is_blacklisted",
    "alerts",
}
ALERT_KEYS = {"code", "severity", "ingredient_name", "title", "detail"}

PREGNANCY_TITLE = {
    "en": "Not recommended during pregnancy",
    "fr": "Déconseillé pendant la grossesse",
}
ALLERGY_TITLE = {
    "en": "Matches your allergy or sensitivity profile",
    "fr": "Correspond à votre profil d'allergie ou de sensibilité",
}
BLACKLIST_TITLE = {"en": "On your blacklist", "fr": "Dans votre liste noire"}
SKIN_TITLE = {
    "en": "May not suit your skin type",
    "fr": "Peut ne pas convenir à votre type de peau",
}


def _url(product_id: uuid.UUID) -> str:
    return f"/api/v1/products/{product_id}/suitability"


async def _ingredient(db_session: AsyncSession, **overrides: Any) -> uuid.UUID:
    ingredient = make_ingredient(**overrides)
    db_session.add(ingredient)
    await db_session.flush()
    return ingredient.id


async def _product_with(db_session: AsyncSession, *ingredient_ids: uuid.UUID | None) -> uuid.UUID:
    product = make_product()
    product.ingredients = [
        ProductIngredient(position=position, raw_text=f"item {position}", ingredient_id=ingredient)
        for position, ingredient in enumerate(ingredient_ids, start=1)
    ]
    db_session.add(product)
    await db_session.flush()
    return product.id


async def _put_profile(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    skin_type: str | None = None,
    pregnant: bool = False,
    conditions: list[str] | None = None,
    allergies: list[uuid.UUID] | None = None,
) -> None:
    response = await client.put(
        PROFILE_URL,
        headers=headers,
        json={
            "skin_type": skin_type,
            "is_pregnant_or_nursing": pregnant,
            "health_conditions": conditions or [],
            "allergy_ingredient_ids": [str(i) for i in allergies or []],
        },
    )
    assert response.status_code == 200, response.text


async def test_suitability_requires_login(client: httpx.AsyncClient) -> None:
    response = await client.get(_url(uuid.uuid4()))

    assert response.status_code == 401


async def test_suitability_unknown_product_is_404(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.get(_url(uuid.uuid4()), headers=headers)

    assert response.status_code == 404


async def test_suitability_without_profile_is_suitable(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    product_id = await _product_with(db_session, await _ingredient(db_session))

    response = await client.get(_url(product_id), headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == RESPONSE_KEYS
    assert body["product_id"] == str(product_id)
    assert body["verdict"] == "suitable"
    assert body["suits_profile"] is True
    assert body["has_risk_alert"] is False
    assert body["is_blacklisted"] is False
    assert body["alerts"] == []


@pytest.mark.parametrize("locale", ["en", "fr"])
async def test_pregnancy_alert(
    client: httpx.AsyncClient, db_session: AsyncSession, locale: str
) -> None:
    headers = await _signed_in(client)
    await _put_profile(client, headers, pregnant=True)
    retinol = await _ingredient(db_session, inci_name="RETINOL")
    product_id = await _product_with(db_session, retinol)

    response = await client.get(_url(product_id), headers={**headers, "Accept-Language": locale})

    body = response.json()
    assert response.status_code == 200
    assert body["verdict"] == "avoid"
    assert body["suits_profile"] is False
    assert body["has_risk_alert"] is True
    [alert] = body["alerts"]
    assert set(alert) == ALERT_KEYS
    assert alert["code"] == "pregnancy_contraindication"
    assert alert["severity"] == "high"
    assert alert["ingredient_name"] == "RETINOL"
    assert alert["title"] == PREGNANCY_TITLE[locale]


@pytest.mark.parametrize("locale", ["en", "fr"])
async def test_declared_allergy_alert(
    client: httpx.AsyncClient, db_session: AsyncSession, locale: str
) -> None:
    headers = await _signed_in(client)
    linalool = await _ingredient(db_session, inci_name="LINALOOL")
    await _put_profile(client, headers, allergies=[linalool])
    product_id = await _product_with(db_session, linalool)

    response = await client.get(_url(product_id), headers={**headers, "Accept-Language": locale})

    [alert] = response.json()["alerts"]
    assert alert["code"] == "allergy_match"
    assert alert["severity"] == "high"
    assert alert["ingredient_name"] == "LINALOOL"
    assert alert["title"] == ALLERGY_TITLE[locale]
    assert response.json()["verdict"] == "avoid"


async def test_allergen_flag_with_sensitive_skin(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    await _put_profile(client, headers, skin_type="sensitive")
    limonene = await _ingredient(db_session, inci_name="LIMONENE", is_allergen=True)
    product_id = await _product_with(db_session, limonene)

    response = await client.get(_url(product_id), headers=headers)

    [alert] = response.json()["alerts"]
    assert alert["code"] == "allergy_match"


@pytest.mark.parametrize("locale", ["en", "fr"])
async def test_blacklisted_ingredient_alert(
    client: httpx.AsyncClient, db_session: AsyncSession, locale: str
) -> None:
    headers = await _signed_in(client)
    parfum = await _ingredient(db_session, inci_name="PARFUM")
    product_id = await _product_with(db_session, parfum)
    added = await client.post(f"{BLACKLIST_URL}/ingredients/{parfum}", headers=headers)
    assert added.status_code == 204

    response = await client.get(_url(product_id), headers={**headers, "Accept-Language": locale})

    body = response.json()
    [alert] = body["alerts"]
    assert alert["code"] == "blacklisted"
    assert alert["severity"] == "high"
    assert alert["ingredient_name"] == "PARFUM"
    assert alert["title"] == BLACKLIST_TITLE[locale]
    assert body["is_blacklisted"] is True
    assert body["has_risk_alert"] is True
    assert body["verdict"] == "avoid"


async def test_blacklisted_product_has_no_alert(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    product_id = await _product_with(db_session, await _ingredient(db_session))
    added = await client.post(f"{BLACKLIST_URL}/products/{product_id}", headers=headers)
    assert added.status_code == 204

    response = await client.get(_url(product_id), headers=headers)

    body = response.json()
    assert body["alerts"] == []
    assert body["is_blacklisted"] is True
    assert body["has_risk_alert"] is True
    assert body["verdict"] == "avoid"
    assert body["suits_profile"] is False


@pytest.mark.parametrize("locale", ["en", "fr"])
async def test_drying_ingredient_for_dry_skin(
    client: httpx.AsyncClient, db_session: AsyncSession, locale: str
) -> None:
    headers = await _signed_in(client)
    await _put_profile(client, headers, skin_type="dry")
    alcohol = await _ingredient(db_session, inci_name="ALCOHOL DENAT.")
    product_id = await _product_with(db_session, alcohol)

    response = await client.get(_url(product_id), headers={**headers, "Accept-Language": locale})

    body = response.json()
    [alert] = body["alerts"]
    assert alert["code"] == "skin_type_mismatch"
    assert alert["severity"] == "medium"
    assert alert["title"] == SKIN_TITLE[locale]
    assert body["verdict"] == "caution"


@pytest.mark.parametrize("locale", ["en", "fr"])
async def test_occlusive_for_acne_prone(
    client: httpx.AsyncClient, db_session: AsyncSession, locale: str
) -> None:
    headers = await _signed_in(client)
    await _put_profile(client, headers, conditions=["acne_prone"])
    petrolatum = await _ingredient(db_session, inci_name="PETROLATUM")
    product_id = await _product_with(db_session, petrolatum)

    response = await client.get(_url(product_id), headers={**headers, "Accept-Language": locale})

    [alert] = response.json()["alerts"]
    assert alert["code"] == "skin_type_mismatch"
    assert alert["title"] == SKIN_TITLE[locale]
    assert response.json()["verdict"] == "caution"


async def test_unmatched_ingredient_is_not_checked(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    await _put_profile(client, headers, pregnant=True)
    product_id = await _product_with(db_session, None)

    response = await client.get(_url(product_id), headers=headers)

    assert response.status_code == 200
    assert response.json()["alerts"] == []
    assert response.json()["verdict"] == "suitable"


async def test_high_alerts_come_before_medium(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    await _put_profile(client, headers, skin_type="dry", pregnant=True)
    alcohol = await _ingredient(db_session, inci_name="ALCOHOL DENAT.")
    retinol = await _ingredient(db_session, inci_name="RETINOL")
    product_id = await _product_with(db_session, alcohol, retinol)

    response = await client.get(_url(product_id), headers=headers)

    severities = [alert["severity"] for alert in response.json()["alerts"]]
    assert severities == ["high", "medium"]
    assert response.json()["verdict"] == "avoid"
