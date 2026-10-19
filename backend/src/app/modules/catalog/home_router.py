"""HTTP endpoints for the home feed (story 1)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.modules.catalog.home_service import DEFAULT_LIMIT, HomeFeedService
from app.modules.catalog.schemas import HomeFeedOut, HomeSectionOut

router = APIRouter()

_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "Invalid cursor or limit."},
    404: {"model": ProblemDetails, "description": "Unknown section."},
}


def get_home_feed_service(request: Request, session: SessionDep) -> HomeFeedService:
    feed_date = getattr(request.app.state.settings, "home_feed_date", None)
    return HomeFeedService(session, feed_date=feed_date)


HomeServiceDep = Annotated[HomeFeedService, Depends(get_home_feed_service)]


@router.get(
    "",
    response_model=HomeFeedOut,
    responses={400: _ERRORS[400]},
    summary="Home feed sections",
)
async def get_home_feed(
    service: HomeServiceDep,
    locale: LocaleDep,
    limit: Annotated[int, Query(description="Page size for product shelves.")] = DEFAULT_LIMIT,
) -> HomeFeedOut:
    """Category grid, top-rated (daily rotation), and recently added. Each product shelf
    has its own `next_cursor` for infinite scroll."""
    return await service.get_feed(locale, limit=limit)


@router.get(
    "/sections/{section_id}",
    response_model=HomeSectionOut,
    responses=_ERRORS,
    summary="Load more items for one home section",
)
async def get_home_section(
    section_id: str,
    service: HomeServiceDep,
    locale: LocaleDep,
    cursor: Annotated[str | None, Query(description="Opaque cursor from a previous page.")] = None,
    limit: Annotated[int, Query(description="Page size.")] = DEFAULT_LIMIT,
) -> HomeSectionOut:
    return await service.get_section(section_id, locale, cursor=cursor, limit=limit)
