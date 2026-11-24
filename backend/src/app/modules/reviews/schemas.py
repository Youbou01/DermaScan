"""Public DTOs and request/response schemas for the reviews module."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.reviews.enums import ReviewSource

ExternalReviewStatus = Literal["fresh", "stale", "unavailable", "refreshing"]


class CreateReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=1, le=5, description="Star rating from 1 to 5.")
    body: str = Field(min_length=1, max_length=2000, description="Review comment text.")

    @field_validator("body", mode="before")
    @classmethod
    def _strip_body(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ReviewOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    product_id: uuid.UUID
    source: ReviewSource
    author_name: str
    rating: int | None
    body: str
    external_url: str | None = None
    created_at: datetime


class ProductReviewsPageOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: uuid.UUID
    avg_rating: float | None = Field(
        description="Average rating (1.0-5.0), or null when no rated reviews exist."
    )
    review_count: int = Field(description="Total number of reviews for this product.")
    external_source_status: ExternalReviewStatus = Field(
        description="Status of external Reddit reviews cache."
    )
    items: list[ReviewOut]
    next_cursor: str | None = Field(
        description="Opaque cursor for next page, or null on the last page."
    )


class UserReviewHistoryItemOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_brand: str | None
    product_image_url: str | None
    rating: int | None
    body: str
    source: ReviewSource
    created_at: datetime


class UserReviewsPageOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[UserReviewHistoryItemOut]
    next_cursor: str | None = Field(
        description="Opaque cursor for next page, or null on the last page."
    )
