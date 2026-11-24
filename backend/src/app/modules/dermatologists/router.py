"""Public endpoint for curated dermatologist recommendations."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.core.dependencies import LocaleDep, SessionDep
from app.core.errors import ProblemDetails
from app.core.security import OptionalUserIdDep
from app.modules.dermatologists.schemas import RecommendationsOut
from app.modules.dermatologists.service import get_recommendations_for_user

router = APIRouter()
SkinTypeQuery = Annotated[
    Literal["normal", "dry", "oily", "combination", "sensitive"] | None,
    Query(description="Optional skin type. Omit to use a signed-in user's saved preference."),
]


@router.get(
    "/recommendations",
    response_model=RecommendationsOut,
    responses={401: {"model": ProblemDetails}, 422: {"model": ProblemDetails}},
    summary="Get curated dermatologist skin care guidance",
)
async def get_recommendations(
    session: SessionDep,
    user_id: OptionalUserIdDep,
    locale: LocaleDep,
    skin_type: SkinTypeQuery = None,
) -> RecommendationsOut:
    return await get_recommendations_for_user(session, user_id, skin_type, locale)
