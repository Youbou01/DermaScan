"""HTTP endpoints for the category browse tree."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import LocaleDep, SessionDep
from app.modules.catalog.category_service import CategoryService
from app.modules.catalog.schemas import CategoryNodeOut

router = APIRouter()


def get_category_service(session: SessionDep) -> CategoryService:
    return CategoryService(session)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


@router.get(
    "",
    response_model=list[CategoryNodeOut],
    summary="List the category tree",
)
async def list_categories(service: CategoryServiceDep, locale: LocaleDep) -> list[CategoryNodeOut]:
    """Top-level categories with children. Names follow `Accept-Language`."""
    return await service.get_tree(locale)
