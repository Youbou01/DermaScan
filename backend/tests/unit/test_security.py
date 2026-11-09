import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError
from app.core.security import (
    CurrentUserIdDep,
    OptionalUserIdDep,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.main import create_app


def make_token(
    user_id: uuid.UUID,
    token_type: str,
    expires_in: timedelta,
    secret: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(
        payload,
        secret or settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def make_app() -> FastAPI:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/test",
    )
    app = create_app(settings)

    @app.get("/_test/me")
    async def me(user_id: CurrentUserIdDep) -> dict[str, str]:
        return {"user_id": str(user_id)}

    @app.get("/_test/maybe")
    async def maybe(user_id: OptionalUserIdDep) -> dict[str, str | None]:
        return {"user_id": str(user_id) if user_id else None}

    return app


@pytest.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=make_app(), raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def test_password_hash_and_verify() -> None:
    password_hash = hash_password("my-secret-password")

    assert password_hash != "my-secret-password"  # noqa: S105
    assert verify_password("my-secret-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_round_trip() -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id)

    assert decode_token(token, "access") == user_id


def test_refresh_token_round_trip() -> None:
    user_id = uuid.uuid4()

    token = create_refresh_token(user_id)

    assert decode_token(token, "refresh") == user_id


def test_refresh_token_is_not_accepted_as_access_token() -> None:
    token = create_refresh_token(uuid.uuid4())

    with pytest.raises(UnauthorizedError):
        decode_token(token, "access")


def test_access_token_is_not_accepted_as_refresh_token() -> None:
    token = create_access_token(uuid.uuid4())

    with pytest.raises(UnauthorizedError):
        decode_token(token, "refresh")


def test_expired_token_is_rejected() -> None:
    token = make_token(uuid.uuid4(), "access", timedelta(minutes=-1))

    with pytest.raises(UnauthorizedError):
        decode_token(token, "access")


def test_invalid_signature_is_rejected() -> None:
    token = make_token(
        uuid.uuid4(),
        "access",
        timedelta(minutes=5),
        secret="another-secret-key-that-is-long-enough",  # noqa: S106
    )

    with pytest.raises(UnauthorizedError):
        decode_token(token, "access")


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(UnauthorizedError):
        decode_token("not-a-jwt", "access")


async def test_current_user_without_header_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/me")

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"


async def test_current_user_with_valid_token(client: httpx.AsyncClient) -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"user_id": str(user_id)}


async def test_current_user_with_invalid_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


async def test_optional_user_without_header_returns_none(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/maybe")

    assert response.status_code == 200
    assert response.json() == {"user_id": None}


async def test_optional_user_with_invalid_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/maybe", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
