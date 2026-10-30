"""Public data shapes of the catalog module. These ARE the JSON the mobile app receives:
changing a field name or type is a breaking API change (mention it in the PR)."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RiskLevel
from app.modules.catalog.enums import EnrichmentStatus, ProductSource


class CategoryOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str = Field(description="Stable key, e.g. 'moisturizer'. Use it for icons and i18n.")
    name: str = Field(description="Display name in the response language (English fallback).")


class CategoryNodeOut(BaseModel):
    """A category in the browse tree (top-level or child)."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(description="Stable key shared with the mobile app and seed files.")
    name: str = Field(description="Display name in the response language (English fallback).")
    children: list[CategoryNodeOut] = Field(default_factory=list)


class ProductIngredientOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    position: int = Field(description="1-based position on the label (decreasing amount).")
    name: str = Field(description="The ingredient exactly as printed on this product's label.")
    inci_name: str | None = Field(
        description="Standard INCI name, when the ingredient is recognized."
    )
    matched: bool = Field(description="False when we do not recognize this ingredient yet.")
    risk_level: RiskLevel = Field(description="'unknown' when not recognized or not rated.")
    rationale: str | None = Field(description="Why it is rated this way, in the response language.")
    rating: float | None = Field(default=None, description="0.0-10.0 scale, 10 = least concern.")
    summary: str | None = Field(default=None, description="Plain-language function summary.")
    confidence: float | None = Field(default=None, description="Rating confidence 0.0-1.0.")


class ProductDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    barcode: str = Field(description="GTIN-13.")
    name: str
    brand: str | None
    image_url: str | None
    category: CategoryOut | None
    score: int | None = Field(description="0-100, or null when the product is not scored.")
    score_band: RiskLevel = Field(description="'unknown' means insufficient data, NOT safe.")
    score_coverage: float | None = Field(description="Share (0-1) of ingredients we could rate.")
    score_is_estimated: bool = Field(default=False, description="True when confidence K < 0.60.")
    ingredients: list[ProductIngredientOut] = Field(description="In label order.")


class ProductCardOut(BaseModel):
    """Light product row for home shelves and search results (not the full detail page)."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    brand: str | None
    image_url: str | None
    score: int | None = Field(description="0-100, or null when not scored.")
    score_band: RiskLevel | None = Field(
        description="Null when the product has no score; 'unknown' means insufficient data."
    )
    score_is_estimated: bool = Field(default=False, description="True when confidence K < 0.60.")
    category_slug: str | None


class HomeSectionOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable section id, e.g. 'top_rated'.")
    type: str = Field(description="Section kind for the client layout.")
    title: str = Field(description="Localized section title.")
    items: list[CategoryOut | ProductCardOut]
    next_cursor: str | None = Field(description="Opaque cursor for the next page, or null.")


class HomeFeedOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    sections: list[HomeSectionOut]


class CreateProductInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    barcode: str
    name: str
    source: ProductSource = ProductSource.OPEN_BEAUTY_FACTS
    source_id: str
    brand_name: str | None = None
    category_slug: str | None = None
    image_url: str | None = None
    raw_ingredients_text: str = ""
    source_lang: str | None = None
    name_i18n: dict[str, str] = Field(default_factory=dict)
    field_provenance: dict[str, Any] = Field(default_factory=dict)
    ingredients: list[tuple[int, str, uuid.UUID | None]] = Field(default_factory=list)


class ProductUpsert(BaseModel):
    """Canonical DTO for publishing enriched or curated products into the catalog."""

    model_config = ConfigDict(frozen=True)

    barcode: str
    name: str
    source: ProductSource = ProductSource.OPEN_BEAUTY_FACTS
    source_id: str
    source_lang: str | None = None
    name_i18n: dict[str, str] = Field(default_factory=dict)
    brand_name: str | None = None
    category_slug: str | None = None
    image_url: str | None = None
    image_source_url: str | None = None
    raw_ingredients_text: str = ""
    ingredients: list[tuple[int, str, uuid.UUID | None]] = Field(default_factory=list)
    field_provenance: dict[str, Any] = Field(default_factory=dict)
    enrichment_status: EnrichmentStatus = EnrichmentStatus.DONE
    data_quality: float | None = None
