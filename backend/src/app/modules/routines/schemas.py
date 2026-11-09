"""Pydantic schemas and public DTOs for the routines module."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.schemas import ProductCardOut
from app.modules.routines.enums import RoutineSlot, RoutineStepType


class RoutineConflictOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(description="Stable error/warning code, e.g. 'retinoid_x_acid'.")
    severity: Literal["high", "moderate"] = Field(
        description="High severity indicates active damage risk; moderate indicates irritation/reduced efficacy."
    )
    product_a_id: uuid.UUID
    product_b_id: uuid.UUID
    product_a_name: str
    product_b_name: str
    ingredient_a: str
    ingredient_b: str
    title: str = Field(description="Localized warning title.")
    detail: str = Field(description="Plain-language chemical reason for the conflict.")
    resolution: str = Field(description="Actionable suggestion to resolve the conflict.")


class RoutineStepIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_order: int = Field(ge=1, description="1-based step position.")
    step_type: RoutineStepType = Field(
        description="Category/type: cleanser, toner, serum, moisturizer, sunscreen, treatment."
    )
    product_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=500)


class UpdateRoutineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[RoutineStepIn] = Field(
        description="Full ordered list of steps to replace existing routine."
    )


class RoutineStepOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID | None = None
    step_order: int
    step_type: RoutineStepType
    product: ProductCardOut
    active_ingredients: list[str] = Field(default_factory=list)
    notes: str | None = None


class RoutineDataOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    slot: RoutineSlot
    name: str
    completed_today: bool
    steps: list[RoutineStepOut]
    conflicts: list[RoutineConflictOut]


class RoutinesListOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    routines: list[RoutineDataOut]


class ConflictCheckOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    has_conflict: bool
    conflicts: list[RoutineConflictOut]


class RecommendedRoutinesOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    skin_type: str
    morning: list[RoutineStepOut]
    evening: list[RoutineStepOut]
