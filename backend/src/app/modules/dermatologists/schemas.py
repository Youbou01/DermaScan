"""Public request and response shapes for curated dermatologist guidance."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.schemas import ProductCardOut


class DermatologistOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    display_name: str
    credentials: str
    specialty: str
    is_verified: bool = Field(
        description="Credential details were checked against the linked source."
    )
    verification_source_url: str


class DermatologistRecommendationOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    dermatologist: DermatologistOut | None
    title: str
    advice: str
    source_title: str
    source_url: str
    related_products: list[ProductCardOut]


class RecommendationsOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendations: list[DermatologistRecommendationOut]
    disclaimer: str
