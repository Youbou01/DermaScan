from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RiskLevel
from app.modules.catalog.enums import EnrichmentStatus
from app.modules.catalog.schemas import ProductIngredientOut


class IngredientInciItem(BaseModel):
    original: str
    inci: str | None = None


class ProductEnrichmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    model_config = ConfigDict(extra="forbid")
    ingredients: list[SingleIngredientRating] = Field(default_factory=list)


class AliasAdjudicationItem(BaseModel):
    token: str
    matched_candidate: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str | None = None


class AliasAdjudicationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    adjudications: list[AliasAdjudicationItem] = Field(default_factory=list)


class OcrIngredientsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingredients_text: str = Field(
        description="Raw ingredients list transcribed from the product photo"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence of the transcription between 0 and 1"
    )
    is_readable: bool = Field(description="Whether the ingredient label is legible and complete")


class InciNormalizationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original: str
    inci: str | None = None


class InciNormalizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredients: list[InciNormalizationItem] = Field(default_factory=list)


class ProductSummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summaries: dict[str, str] = Field(default_factory=dict)


class TextAnalysisIn(BaseModel):
    """A manually entered ingredient label for immediate, non-persistent analysis."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=3, max_length=10_000, description="Raw ingredient label text.")
    product_name: str | None = Field(default=None, max_length=255)


class InstantAnalysisOut(BaseModel):
    """Synchronous score and ingredient projection for an unlisted product label."""

    model_config = ConfigDict(frozen=True)

    extracted_text: str = Field(description="Extracted or submitted ingredient text.")
    score: int | None = Field(description="Calculated score (0-100), or null if unrateable.")
    score_band: RiskLevel = Field(description="Risk band: low, moderate, high, or unknown.")
    score_coverage: float = Field(
        ge=0.0,
        le=1.0,
        description="Share of parsed ingredients recognized by the ingredient reference.",
    )
    score_is_estimated: bool = Field(default=False)
    summary: str = Field(description="Plain-language formulation overview.")
    ingredients: list[ProductIngredientOut] = Field(
        description="Parsed ingredient breakdown in label order."
    )


@dataclass(slots=True, frozen=True)
class EnrichmentOutcome:
    status: EnrichmentStatus
    reason: str | None = None
    result: ProductEnrichmentResult | None = None
