"""Authenticated API endpoints for the personal library."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.keyset import CursorQuery
from app.core.security import CurrentUserIdDep
from app.modules.personal_library.schemas import ProductPageOut, SavedProductStatusOut
from app.modules.personal_library.service import PersonalLibraryService

router = APIRouter()

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
}


def get_personal_library_service(session: SessionDep) -> PersonalLibraryService:
    return PersonalLibraryService(session)


ServiceDep = Annotated[PersonalLibraryService, Depends(get_personal_library_service)]
SavedLimit = Annotated[int, Query(ge=1, le=50)]
RecentLimit = Annotated[int, Query(ge=1, le=20)]


@router.get("/saved", response_model=ProductPageOut, responses=_ERRORS)
async def get_saved_products(
    service: ServiceDep,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
    limit: SavedLimit = 20,
    cursor: CursorQuery = None,
) -> ProductPageOut:
    return await service.saved_products(user_id, locale, limit, cursor)


@router.put(
    "/saved/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ERRORS,
    summary="Save a product to my library",
)
async def save_product(
    product_id: uuid.UUID,
    service: ServiceDep,
    session: SessionDep,
    user_id: CurrentUserIdDep,
) -> None:
    await service.save_product(user_id, product_id)
    await session.commit()


@router.get(
    "/saved/{product_id}",
    response_model=SavedProductStatusOut,
    responses={401: {"model": ProblemDetails}},
    summary="Check whether a product is in my library",
)
async def get_saved_product_status(
    product_id: uuid.UUID, service: ServiceDep, user_id: CurrentUserIdDep
) -> SavedProductStatusOut:
    return SavedProductStatusOut(saved=await service.is_saved(user_id, product_id))


@router.delete(
    "/saved/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ERRORS,
    summary="Remove a product from my library",
)
async def unsave_product(
    product_id: uuid.UUID,
    service: ServiceDep,
    session: SessionDep,
    user_id: CurrentUserIdDep,
) -> None:
    await service.unsave_product(user_id, product_id)
    await session.commit()


@router.get("/recently-viewed", response_model=ProductPageOut, responses=_ERRORS)
async def get_recently_viewed(
    service: ServiceDep,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
    limit: RecentLimit = 20,
    cursor: CursorQuery = None,
) -> ProductPageOut:
    return await service.recently_viewed(user_id, locale, limit, cursor)


@router.put(
    "/recently-viewed/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ERRORS,
    summary="Record a product in my recently viewed list",
)
async def record_recently_viewed(
    product_id: uuid.UUID,
    service: ServiceDep,
    session: SessionDep,
    user_id: CurrentUserIdDep,
) -> None:
    await service.record_recently_viewed(user_id, product_id)
    await session.commit()
