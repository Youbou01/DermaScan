import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from tests.factories import make_ingredient, make_product

pytestmark = pytest.mark.usefixtures("migrated_database")

PASSWORD = "correct-horse-battery"  # noqa: S105
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"

AUTH_KEYS = {"access_token", "refresh_token", "token_type", "user"}
USER_KEYS = {"id", "email", "display_name"}


async def _register(
    client: httpx.AsyncClient, email: str = "sara@example.com", password: str = PASSWORD
) -> httpx.Response:
    return await client.post(
        REGISTER_URL, json={"email": email, "password": password, "display_name": "Sara"}
    )


# ------------------------------------------------------------------------ register


async def test_register_returns_tokens_and_user(client: httpx.AsyncClient) -> None:
    response = await _register(client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == AUTH_KEYS
    assert body["token_type"] == "bearer"  # noqa: S105
    assert set(body["user"]) == USER_KEYS
    assert body["user"]["email"] == "sara@example.com"
    assert body["user"]["display_name"] == "Sara"
    uuid.UUID(body["user"]["id"])


async def test_register_stores_email_trimmed_and_lowercase(client: httpx.AsyncClient) -> None:
    response = await _register(client, email="  Sara@Example.COM ")

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "sara@example.com"


async def test_register_duplicate_email_is_409(client: httpx.AsyncClient) -> None:
    assert (await _register(client)).status_code == 201

    response = await _register(client)

    assert response.status_code == 409
    assert response.json()["type"] == "urn:skincare:problem:email-already-registered"


async def test_register_duplicate_email_with_other_case_is_409(client: httpx.AsyncClient) -> None:
    assert (await _register(client, email="sara@example.com")).status_code == 201

    response = await _register(client, email="SARA@example.com")

    assert response.status_code == 409


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("not-an-email", PASSWORD),
        ("sara@example", PASSWORD),
        ("sara@example.com", "short"),
        ("sara@example.com", "x" * 129),
    ],
)
async def test_register_rejects_invalid_input(
    client: httpx.AsyncClient, email: str, password: str
) -> None:
    response = await _register(client, email=email, password=password)

    assert response.status_code == 422


# --------------------------------------------------------------------------- login


async def test_login_returns_tokens_and_user(client: httpx.AsyncClient) -> None:
    registered = (await _register(client)).json()

    response = await client.post(
        LOGIN_URL, json={"email": "sara@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == AUTH_KEYS
    assert body["user"]["id"] == registered["user"]["id"]


async def test_login_accepts_email_in_another_case(client: httpx.AsyncClient) -> None:
    await _register(client)

    response = await client.post(
        LOGIN_URL, json={"email": " SARA@Example.com ", "password": PASSWORD}
    )

    assert response.status_code == 200


async def test_login_wrong_password_and_unknown_email_give_same_401(
    client: httpx.AsyncClient,
) -> None:
    await _register(client)

    wrong_password = await client.post(
        LOGIN_URL, json={"email": "sara@example.com", "password": "wrong-password"}
    )
    unknown_email = await client.post(
        LOGIN_URL, json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["type"] == "urn:skincare:problem:invalid-credentials"
    assert unknown_email.json()["type"] == wrong_password.json()["type"]
    assert unknown_email.json()["detail"] == wrong_password.json()["detail"]


# -------------------------------------------------------------------------- refresh


async def test_refresh_returns_new_access_token(client: httpx.AsyncClient) -> None:
    tokens = (await _register(client)).json()

    response = await client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type"}
    assert body["token_type"] == "bearer"  # noqa: S105
    assert body["access_token"]


async def test_refresh_rejects_an_access_token(client: httpx.AsyncClient) -> None:
    tokens = (await _register(client)).json()

    response = await client.post(REFRESH_URL, json={"refresh_token": tokens["access_token"]})

    assert response.status_code == 401


async def test_refresh_rejects_a_garbage_token(client: httpx.AsyncClient) -> None:
    response = await client.post(REFRESH_URL, json={"refresh_token": "not-a-jwt"})

    assert response.status_code == 401


async def test_refresh_rejects_a_deleted_account(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    tokens = (await _register(client)).json()
    await db_session.execute(
        text("DELETE FROM user_account WHERE id = :id"), {"id": tokens["user"]["id"]}
    )

    response = await client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401


async def test_access_token_helper_is_accepted_nowhere_as_refresh(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        REFRESH_URL, json={"refresh_token": create_access_token(uuid.uuid4())}
    )

    assert response.status_code == 401


# -------------------------------------------------------------------------- profile

PROFILE_URL = "/api/v1/profile"
BLACKLIST_URL = "/api/v1/profile/blacklist"
PROFILE_KEYS = {
    "user_id",
    "skin_type",
    "is_pregnant_or_nursing",
    "health_conditions",
    "allergy_ingredient_ids",
    "blacklisted_product_ids",
}


async def _signed_in(client: httpx.AsyncClient) -> dict[str, str]:
    tokens = (await _register(client)).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _new_ingredient(db_session: AsyncSession) -> uuid.UUID:
    ingredient = make_ingredient()
    db_session.add(ingredient)
    await db_session.flush()
    return ingredient.id


async def _new_product(db_session: AsyncSession) -> uuid.UUID:
    product = make_product()
    db_session.add(product)
    await db_session.flush()
    return product.id


async def test_get_profile_without_row_returns_defaults(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.get(PROFILE_URL, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PROFILE_KEYS
    assert body["skin_type"] is None
    assert body["is_pregnant_or_nursing"] is False
    assert body["health_conditions"] == []
    assert body["allergy_ingredient_ids"] == []
    assert body["blacklisted_product_ids"] == []


async def test_put_profile_then_get_returns_the_same_values(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    ingredient_id = await _new_ingredient(db_session)

    put = await client.put(
        PROFILE_URL,
        headers=headers,
        json={
            "skin_type": "dry",
            "is_pregnant_or_nursing": True,
            "health_conditions": ["eczema", "rosacea"],
            "allergy_ingredient_ids": [str(ingredient_id)],
        },
    )
    got = await client.get(PROFILE_URL, headers=headers)

    assert put.status_code == 200
    assert got.status_code == 200
    assert put.json() == got.json()
    body = got.json()
    assert set(body) == PROFILE_KEYS
    assert body["skin_type"] == "dry"
    assert body["is_pregnant_or_nursing"] is True
    assert body["health_conditions"] == ["eczema", "rosacea"]
    assert body["allergy_ingredient_ids"] == [str(ingredient_id)]


async def test_put_profile_rejects_unknown_health_condition(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.put(
        PROFILE_URL, headers=headers, json={"health_conditions": ["Eczema "]}
    )

    assert response.status_code == 422


async def test_put_profile_rejects_unknown_skin_type(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.put(PROFILE_URL, headers=headers, json={"skin_type": "scaly"})

    assert response.status_code == 422


async def test_put_profile_removes_duplicate_conditions(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.put(
        PROFILE_URL, headers=headers, json={"health_conditions": ["eczema", "eczema"]}
    )

    assert response.status_code == 200
    assert response.json()["health_conditions"] == ["eczema"]


async def test_put_profile_unknown_allergy_ingredient_is_404(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.put(
        PROFILE_URL, headers=headers, json={"allergy_ingredient_ids": [str(uuid.uuid4())]}
    )

    assert response.status_code == 404
    assert response.json()["type"] == "urn:skincare:problem:ingredient-not-found"


async def test_put_profile_replaces_the_allergy_set(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    first = await _new_ingredient(db_session)
    second = await _new_ingredient(db_session)
    third = await _new_ingredient(db_session)

    await client.put(
        PROFILE_URL,
        headers=headers,
        json={"allergy_ingredient_ids": [str(first), str(second)]},
    )
    response = await client.put(
        PROFILE_URL,
        headers=headers,
        json={"allergy_ingredient_ids": [str(second), str(third)]},
    )

    assert response.status_code == 200
    assert set(response.json()["allergy_ingredient_ids"]) == {str(second), str(third)}


async def test_put_profile_ignores_blacklisted_product_ids(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    product_id = await _new_product(db_session)

    response = await client.put(
        PROFILE_URL, headers=headers, json={"blacklisted_product_ids": [str(product_id)]}
    )

    assert response.status_code == 200
    assert response.json()["blacklisted_product_ids"] == []


# ------------------------------------------------------------------------ blacklist


async def test_blacklist_product_add_list_and_remove(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    product_id = await _new_product(db_session)
    url = f"{BLACKLIST_URL}/products/{product_id}"

    added = await client.post(url, headers=headers)
    listed = await client.get(BLACKLIST_URL, headers=headers)
    in_profile = await client.get(PROFILE_URL, headers=headers)
    removed = await client.delete(url, headers=headers)
    after = await client.get(BLACKLIST_URL, headers=headers)

    assert added.status_code == 204
    assert added.content == b""
    assert listed.status_code == 200
    assert set(listed.json()) == {"product_ids", "ingredient_ids"}
    assert listed.json()["product_ids"] == [str(product_id)]
    assert in_profile.json()["blacklisted_product_ids"] == [str(product_id)]
    assert removed.status_code == 204
    assert after.json()["product_ids"] == []


async def test_blacklist_product_twice_is_not_an_error(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    product_id = await _new_product(db_session)
    url = f"{BLACKLIST_URL}/products/{product_id}"

    first = await client.post(url, headers=headers)
    second = await client.post(url, headers=headers)
    listed = await client.get(BLACKLIST_URL, headers=headers)

    assert first.status_code == 204
    assert second.status_code == 204
    assert listed.json()["product_ids"] == [str(product_id)]


async def test_blacklist_unknown_product_is_404(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.post(f"{BLACKLIST_URL}/products/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_unblacklist_product_that_is_not_blacklisted_is_204(
    client: httpx.AsyncClient,
) -> None:
    headers = await _signed_in(client)

    response = await client.delete(f"{BLACKLIST_URL}/products/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 204


async def test_blacklist_ingredient_add_list_and_remove(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _signed_in(client)
    ingredient_id = await _new_ingredient(db_session)
    url = f"{BLACKLIST_URL}/ingredients/{ingredient_id}"

    added = await client.post(url, headers=headers)
    again = await client.post(url, headers=headers)
    listed = await client.get(BLACKLIST_URL, headers=headers)
    removed = await client.delete(url, headers=headers)
    after = await client.get(BLACKLIST_URL, headers=headers)

    assert added.status_code == 204
    assert again.status_code == 204
    assert listed.json()["ingredient_ids"] == [str(ingredient_id)]
    assert removed.status_code == 204
    assert after.json()["ingredient_ids"] == []


async def test_blacklist_unknown_ingredient_is_404(client: httpx.AsyncClient) -> None:
    headers = await _signed_in(client)

    response = await client.post(f"{BLACKLIST_URL}/ingredients/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404
    assert response.json()["type"] == "urn:skincare:problem:ingredient-not-found"


async def test_blacklist_is_private_to_each_user(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    owner = await _signed_in(client)
    product_id = await _new_product(db_session)
    await client.post(f"{BLACKLIST_URL}/products/{product_id}", headers=owner)
    other_tokens = (await _register(client, email="other@example.com")).json()
    other = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    response = await client.get(BLACKLIST_URL, headers=other)

    assert response.json() == {"product_ids": [], "ingredient_ids": []}


_SOME_ID = uuid.uuid4()


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", PROFILE_URL),
        ("PUT", PROFILE_URL),
        ("GET", BLACKLIST_URL),
        ("POST", f"{BLACKLIST_URL}/products/{_SOME_ID}"),
        ("DELETE", f"{BLACKLIST_URL}/products/{_SOME_ID}"),
        ("POST", f"{BLACKLIST_URL}/ingredients/{_SOME_ID}"),
        ("DELETE", f"{BLACKLIST_URL}/ingredients/{_SOME_ID}"),
    ],
)
async def test_profile_routes_require_a_token(
    client: httpx.AsyncClient, method: str, url: str
) -> None:
    response = await client.request(method, url, json={} if method == "PUT" else None)

    assert response.status_code == 401
