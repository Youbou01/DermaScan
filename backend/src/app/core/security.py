import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

TokenType = Literal["access", "refresh"]

_password_hash = PasswordHash.recommended()
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def _create_token(user_id: uuid.UUID, token_type: TokenType, lifetime: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    return _create_token(user_id, "access", timedelta(minutes=settings.jwt_access_token_minutes))


def create_refresh_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    return _create_token(user_id, "refresh", timedelta(days=settings.jwt_refresh_token_days))


def decode_token(token: str, token_type: TokenType) -> uuid.UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token") from None
    if payload["type"] != token_type:
        raise UnauthorizedError("Wrong token type")
    try:
        return uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthorizedError("Invalid token subject") from None


async def get_optional_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> uuid.UUID | None:
    if credentials is None:
        return None
    return decode_token(credentials.credentials, "access")


async def get_current_user_id(
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
) -> uuid.UUID:
    if user_id is None:
        raise UnauthorizedError("Missing bearer token")
    return user_id


CurrentUserIdDep = Annotated[uuid.UUID, Depends(get_current_user_id)]
OptionalUserIdDep = Annotated[uuid.UUID | None, Depends(get_optional_user_id)]
