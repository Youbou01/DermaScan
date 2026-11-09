"""HTTP boundary for authenticated routine workflows."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.security import CurrentUserIdDep
from app.modules.routines.enums import RoutineSlot
from app.modules.routines.schemas import (
    ConflictCheckOut,
    RecommendedRoutinesOut,
    RoutineDataOut,
    RoutinesListOut,
    UpdateRoutineIn,
)
from app.modules.routines.service import RoutineService

router = APIRouter()

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
}


def get_routine_service(session: SessionDep) -> RoutineService:
    return RoutineService(session)


ServiceDep = Annotated[RoutineService, Depends(get_routine_service)]


@router.get("", response_model=RoutinesListOut, responses=_ERRORS)
async def get_routines(
    service: ServiceDep, user_id: CurrentUserIdDep, locale: LocaleDep
) -> RoutinesListOut:
    return RoutinesListOut(routines=await service.list_routines(user_id, locale))


@router.get("/recommendations", response_model=RecommendedRoutinesOut, responses=_ERRORS)
async def get_recommendations(
    service: ServiceDep,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
    skin_type: Literal["normal", "dry", "oily", "combination", "sensitive"] = "normal",
) -> RecommendedRoutinesOut:
    # The optional profile lookup is intentionally deferred until identity exposes a
    # public profile reader; the explicit query parameter keeps this boundary decoupled.
    del user_id
    return await service.recommendations(skin_type, locale)


@router.put("/{slot}", response_model=RoutineDataOut, responses=_ERRORS)
async def replace_routine(
    slot: RoutineSlot,
    data: UpdateRoutineIn,
    service: ServiceDep,
    session: SessionDep,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
) -> RoutineDataOut:
    result = await service.replace_routine(user_id, slot, data.steps, locale)
    await session.commit()
    return result


@router.post(
    "/{slot}/check-conflict/{product_id}", response_model=ConflictCheckOut, responses=_ERRORS
)
async def check_product_conflict(
    slot: RoutineSlot,
    product_id: uuid.UUID,
    service: ServiceDep,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
) -> ConflictCheckOut:
    return await service.check_product_conflict(user_id, slot, product_id, locale)


@router.post("/{slot}/complete", response_model=RoutineDataOut, responses=_ERRORS)
async def toggle_routine_completion(
    slot: RoutineSlot,
    service: ServiceDep,
    session: SessionDep,
    user_id: CurrentUserIdDep,
    locale: LocaleDep,
) -> RoutineDataOut:
    result = await service.toggle_completion(user_id, slot, locale)
    await session.commit()
    return result
