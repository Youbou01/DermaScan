"""HTTP endpoints for product reviews and personal review history."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.keyset import DEFAULT_LIMIT, CursorQuery, LimitQuery
from app.core.security import CurrentUserIdDep
from app.modules.reviews.schemas import (
    CreateReviewIn,
    ProductReviewsPageOut,
    ReviewOut,
    UserReviewsPageOut,
)
from app.modules.reviews.service import ReviewService

product_reviews_router = APIRouter()
user_reviews_router = APIRouter()

_LIST_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetails, "description": "Product not found."},
    422: {"model": ProblemDetails, "description": "Invalid identifier or cursor."},
}
_CREATE_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Authentication required."},
    404: {"model": ProblemDetails, "description": "Product not found."},
    409: {"model": ProblemDetails, "description": "Duplicate review for this product."},
    422: {"model": ProblemDetails, "description": "Invalid rating or review body."},
}
_USER_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Authentication required."},
    422: {"model": ProblemDetails, "description": "Invalid cursor."},
}


def get_review_service(session: SessionDep) -> ReviewService:
    return ReviewService(session)


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]


@product_reviews_router.get(
    "/{product_id}/reviews",
    response_model=ProductReviewsPageOut,
    responses=_LIST_ERRORS,
    summary="List product reviews from app and external sources",
)
async def list_product_reviews(
    product_id: uuid.UUID,
    service: ReviewServiceDep,
    locale: LocaleDep,
    limit: LimitQuery = DEFAULT_LIMIT,
    cursor: CursorQuery = None,
) -> ProductReviewsPageOut:
    return await service.list_product_reviews(product_id, limit=limit, cursor=cursor, locale=locale)


@product_reviews_router.post(
    "/{product_id}/reviews",
    status_code=status.HTTP_201_CREATED,
    response_model=ReviewOut,
    responses=_CREATE_ERRORS,
    summary="Post a product review",
)
async def create_product_review(
    product_id: uuid.UUID,
    payload: CreateReviewIn,
    user_id: CurrentUserIdDep,
    service: ReviewServiceDep,
) -> ReviewOut:
    return await service.create_review(product_id=product_id, user_id=user_id, payload=payload)


@user_reviews_router.get(
    "/reviews",
    response_model=UserReviewsPageOut,
    responses=_USER_ERRORS,
    summary="List the signed-in user's reviewed products history",
)
async def list_my_reviews(
    user_id: CurrentUserIdDep,
    service: ReviewServiceDep,
    locale: LocaleDep,
    limit: LimitQuery = DEFAULT_LIMIT,
    cursor: CursorQuery = None,
) -> UserReviewsPageOut:
    return await service.list_user_reviews(user_id, limit=limit, cursor=cursor, locale=locale)
