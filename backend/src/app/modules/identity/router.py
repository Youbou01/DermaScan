"""HTTP endpoints of the identity module. No logic here: parse input, call the service."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.security import CurrentUserIdDep
from app.modules.identity.schemas import (
    AccessTokenOut,
    AuthTokensOut,
    BlacklistOut,
    LoginRequest,
    ProfileOut,
    ProfileUpdateIn,
    RefreshRequest,
    RegisterRequest,
    SuitabilityOut,
)
from app.modules.identity.service import IdentityService

auth_router = APIRouter()
profile_router = APIRouter()
suitability_router = APIRouter()

_INVALID_BODY: dict[int | str, dict[str, Any]] = {
    422: {"model": ProblemDetails, "description": "Malformed or invalid request."},
}
_REGISTER_ERRORS: dict[int | str, dict[str, Any]] = {
    409: {"model": ProblemDetails, "description": "Email already registered."},
    **_INVALID_BODY,
}
_AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Invalid credentials or token."},
    **_INVALID_BODY,
}
_PROFILE_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Missing or invalid access token."},
    404: {"model": ProblemDetails, "description": "Unknown ingredient id."},
    **_INVALID_BODY,
}
_BLACKLIST_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Missing or invalid access token."},
    404: {"model": ProblemDetails, "description": "Unknown product or ingredient id."},
    **_INVALID_BODY,
}


_SUITABILITY_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Missing or invalid access token."},
    404: {"model": ProblemDetails, "description": "Unknown product id."},
    **_INVALID_BODY,
}


def get_identity_service(session: SessionDep) -> IdentityService:
    return IdentityService(session)


ServiceDep = Annotated[IdentityService, Depends(get_identity_service)]


# ------------------------------------------------------------------------------ auth


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthTokensOut,
    responses=_REGISTER_ERRORS,
    summary="Create an account",
)
async def register(payload: RegisterRequest, service: ServiceDep) -> AuthTokensOut:
    return await service.register(payload)


@auth_router.post(
    "/login",
    response_model=AuthTokensOut,
    responses=_AUTH_ERRORS,
    summary="Sign in with email and password",
)
async def login(payload: LoginRequest, service: ServiceDep) -> AuthTokensOut:
    return await service.login(payload)


@auth_router.post(
    "/refresh",
    response_model=AccessTokenOut,
    responses=_AUTH_ERRORS,
    summary="Get a new access token from a refresh token",
)
async def refresh(payload: RefreshRequest, service: ServiceDep) -> AccessTokenOut:
    return await service.refresh(payload.refresh_token)


# --------------------------------------------------------------------------- profile


@profile_router.get(
    "",
    response_model=ProfileOut,
    responses=_PROFILE_ERRORS,
    summary="Get my health profile",
)
async def get_profile(user_id: CurrentUserIdDep, service: ServiceDep) -> ProfileOut:
    return await service.get_profile(user_id)


@profile_router.put(
    "",
    response_model=ProfileOut,
    responses=_PROFILE_ERRORS,
    summary="Replace my health profile and allergies",
)
async def put_profile(
    payload: ProfileUpdateIn, user_id: CurrentUserIdDep, service: ServiceDep
) -> ProfileOut:
    return await service.put_profile(user_id, payload)


@profile_router.get(
    "/blacklist",
    response_model=BlacklistOut,
    responses=_PROFILE_ERRORS,
    summary="List my blacklisted products and ingredients",
)
async def get_blacklist(user_id: CurrentUserIdDep, service: ServiceDep) -> BlacklistOut:
    return await service.get_blacklist(user_id)


@profile_router.post(
    "/blacklist/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_BLACKLIST_ERRORS,
    summary="Blacklist a product",
)
async def blacklist_product(
    product_id: uuid.UUID, user_id: CurrentUserIdDep, service: ServiceDep
) -> None:
    await service.add_blacklisted_product(user_id, product_id)


@profile_router.delete(
    "/blacklist/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_BLACKLIST_ERRORS,
    summary="Remove a product from my blacklist",
)
async def unblacklist_product(
    product_id: uuid.UUID, user_id: CurrentUserIdDep, service: ServiceDep
) -> None:
    await service.remove_blacklisted_product(user_id, product_id)


@profile_router.post(
    "/blacklist/ingredients/{ingredient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_BLACKLIST_ERRORS,
    summary="Blacklist an ingredient",
)
async def blacklist_ingredient(
    ingredient_id: uuid.UUID, user_id: CurrentUserIdDep, service: ServiceDep
) -> None:
    await service.add_blacklisted_ingredient(user_id, ingredient_id)


@profile_router.delete(
    "/blacklist/ingredients/{ingredient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_BLACKLIST_ERRORS,
    summary="Remove an ingredient from my blacklist",
)
async def unblacklist_ingredient(
    ingredient_id: uuid.UUID, user_id: CurrentUserIdDep, service: ServiceDep
) -> None:
    await service.remove_blacklisted_ingredient(user_id, ingredient_id)


# ----------------------------------------------------------------------- suitability


@suitability_router.get(
    "/{product_id}/suitability",
    response_model=SuitabilityOut,
    responses=_SUITABILITY_ERRORS,
    summary="Does this product suit my profile?",
)
async def get_suitability(
    product_id: uuid.UUID,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
    service: ServiceDep,
) -> SuitabilityOut:
    return await service.get_suitability(user_id, product_id, locale)
