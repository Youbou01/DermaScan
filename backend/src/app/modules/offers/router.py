"""HTTP boundary for the offers of a product (authenticated)."""

import uuid
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.security import CurrentUserIdDep
from app.modules.offers.schemas import OfferListOut
from app.modules.offers.service import OfferService

router = APIRouter()

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
}


def get_offer_service(session: SessionDep) -> OfferService:
    return OfferService(session)


ServiceDep = Annotated[OfferService, Depends(get_offer_service)]


@router.get("/{product_id}/offers", response_model=OfferListOut, responses=_ERRORS)
async def list_product_offers(
    product_id: uuid.UUID,
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
) -> OfferListOut:
    del user_id  # authentication only: offers are not user-specific
    stale_after = timedelta(days=request.app.state.settings.offer_stale_after_days)
    return await service.list_offers(product_id, locale, stale_after)
