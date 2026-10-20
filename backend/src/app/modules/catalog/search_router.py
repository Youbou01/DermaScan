"""HTTP endpoints for product search and filters (included by catalog/router.py)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import SessionDep
from app.core.enums import RiskLevel
from app.core.errors import ProblemDetails
from app.core.keyset import DEFAULT_LIMIT, CursorQuery, LimitQuery, Page
from app.modules.catalog.search_schemas import ProductSummary
from app.modules.catalog.search_service import ProductSearchService

router = APIRouter()

_ERRORS: dict[int | str, dict[str, Any]] = {
    422: {"model": ProblemDetails, "description": "Invalid query, cursor or score range."},
}


def get_search_service(session: SessionDep) -> ProductSearchService:
    return ProductSearchService(session)


SearchServiceDep = Annotated[ProductSearchService, Depends(get_search_service)]


@router.get(
    "/search",
    response_model=Page[ProductSummary],
    responses=_ERRORS,
    summary="Search products by name (accent-insensitive, typo-tolerant)",
)
async def search_products(
    service: SearchServiceDep,
    q: Annotated[str, Query(min_length=1, max_length=100, description="Name to look for.")],
    limit: LimitQuery = DEFAULT_LIMIT,
    cursor: CursorQuery = None,
) -> Page[ProductSummary]:
    return await service.search_by_name(q, limit=limit, cursor=cursor)


@router.get(
    "/filter",
    response_model=Page[ProductSummary],
    responses=_ERRORS,
    summary="Filter scored products, best score first",
)
async def filter_products(
    service: SearchServiceDep,
    category: Annotated[
        str | None, Query(description="Category slug; child categories are included.")
    ] = None,
    band: Annotated[list[RiskLevel] | None, Query(description="One or more score bands.")] = None,
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    max_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    include: Annotated[
        list[str] | None, Query(max_length=10, description="Must contain all of these.")
    ] = None,
    exclude: Annotated[
        list[str] | None, Query(max_length=10, description="Must contain none of these.")
    ] = None,
    limit: LimitQuery = DEFAULT_LIMIT,
    cursor: CursorQuery = None,
) -> Page[ProductSummary]:
    return await service.filter_products(
        category=category,
        bands=band,
        min_score=min_score,
        max_score=max_score,
        include=include,
        exclude=exclude,
        limit=limit,
        cursor=cursor,
    )
