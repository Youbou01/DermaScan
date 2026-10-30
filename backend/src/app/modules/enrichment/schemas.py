from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.modules.catalog.enums import EnrichmentStatus


class IngredientInciItem(BaseModel):
    original: str
    inci: str | None = None


class ProductEnrichmentResult(BaseModel):
    is_skincare: bool
    is_skincare_confidence: float = Field(ge=0.0, le=1.0)
    brand: str | None = None
    brand_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    name_clean: str
    name_i18n: dict[str, str] = Field(default_factory=dict)
    source_lang: str = "en"
    category_slug: str | None = None
    category_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    ingredients_inci: list[IngredientInciItem] = Field(default_factory=list)
    ingredients_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)


class IngredientAliasItem(BaseModel):
    name: str
    language: str | None = None


class SingleIngredientRating(BaseModel):
    inci: str
    rating: float = Field(ge=0.0, le=10.0)
    confidence: float = Field(ge=0.0, le=1.0)
    functions: list[str] = Field(default_factory=list)
    key_concerns: list[str] = Field(default_factory=list)
    evidence: str = "well_established"
    summary: dict[str, str] = Field(default_factory=dict)
    concern_note: dict[str, str] | None = None
    aliases: list[IngredientAliasItem] = Field(default_factory=list)


class IngredientRatingBatchResult(BaseModel):
    ingredients: list[SingleIngredientRating] = Field(default_factory=list)


class AliasAdjudicationItem(BaseModel):
    token: str
    matched_candidate: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str | None = None


class AliasAdjudicationResult(BaseModel):
    adjudications: list[AliasAdjudicationItem] = Field(default_factory=list)


@dataclass(slots=True, frozen=True)
class EnrichmentOutcome:
    status: EnrichmentStatus
    reason: str | None = None
    result: ProductEnrichmentResult | None = None
