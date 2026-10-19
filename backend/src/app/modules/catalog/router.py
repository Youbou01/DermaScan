"""HTTP endpoints of the catalog module. No logic here: parse input, call the service."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.modules.catalog.schemas import ProductDetail
from app.modules.catalog.search_router import router as search_router
from app.modules.catalog.service import CatalogService

router = APIRouter()
# Must come before "/{product_id}", otherwise "search" is parsed as an id.
router.include_router(search_router)

_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetails, "description": "No such product."},
    422: {"model": ProblemDetails, "description": "Malformed barcode or identifier."},
}


def get_catalog_service(session: SessionDep) -> CatalogService:
    return CatalogService(session)


ServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


@router.get(
    "/by-barcode/{barcode}",
    response_model=ProductDetail,
    responses=_ERRORS,
    summary="Get a product by scanning its barcode",
)
async def get_product_by_barcode(
    barcode: str, service: ServiceDep, locale: LocaleDep
) -> ProductDetail:
    """EAN-13, UPC-A and EAN-8 are accepted (spaces and hyphens are ignored); the product is
    stored and returned under its 13-digit form. A valid barcode we do not know is a 404
    with type `urn:skincare:problem:product-not-found`; a malformed one is a 422
    `invalid-barcode`."""
    return await service.get_product_detail_by_barcode(barcode, locale)


@router.get(
    "/{product_id}",
    response_model=ProductDetail,
    responses=_ERRORS,
    summary="Get a product by id",
)
async def get_product(
    product_id: uuid.UUID, service: ServiceDep, locale: LocaleDep
) -> ProductDetail:
    return await service.get_product_detail(product_id, locale)
