"""Public data shapes of the ingredients module (DTOs). Plain, immutable, no database links."""

import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.core.enums import RiskLevel


class MatchType(StrEnum):
    EXACT = "exact"  # the whole label item is a known name
    COMPONENT = "component"  # found through a part of the item, e.g. "Aqua (Water)" -> "Aqua"
    NONE = "none"  # not recognized: goes to the review queue, never guessed


class IngredientMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_text: str
    ingredient_id: uuid.UUID | None  # None exactly when match_type is NONE
    match_type: MatchType


class IngredientInfo(BaseModel):
    """What the rest of the app needs to know about one ingredient."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    inci_name: str
    risk_level: RiskLevel
    rationale: str | None  # in the requested locale, English fallback, None if no text exists
    source_ref: str | None


class IngredientSuggestion(BaseModel):
    """A *possible* match for a human to confirm. Never used to compute a score."""

    model_config = ConfigDict(frozen=True)

    ingredient_id: uuid.UUID
    inci_name: str
    alias: str
    similarity: float  # 0..1
