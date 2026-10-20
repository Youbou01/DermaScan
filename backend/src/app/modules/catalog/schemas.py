"""Public data shapes of the catalog module. These ARE the JSON the mobile app receives:
changing a field name or type is a breaking API change (mention it in the PR)."""

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RiskLevel

HomeSectionType = Literal["category_grid", "top_rated", "recently_added"]


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
    category_slug: str | None


<<<<<<< HEAD
class CategoryGridSectionOut(BaseModel):
    """Home section whose items are top-level categories (no pagination)."""

    model_config = ConfigDict(frozen=True)

    id: Literal["categories"] = "categories"
    type: Literal["category_grid"] = "category_grid"
    title: str = Field(description="Localized section title.")
    items: list[CategoryOut]
    next_cursor: None = Field(description="Always null: the category grid is not paginated.")


class ProductShelfSectionOut(BaseModel):
    """Home section whose items are light product cards (keyset-paginated)."""

    model_config = ConfigDict(frozen=True)

    id: Literal["top_rated", "recently_added"]
    type: Literal["top_rated", "recently_added"]
    title: str = Field(description="Localized section title.")
    items: list[ProductCardOut]
    next_cursor: str | None = Field(description="Opaque cursor for the next page, or null.")


HomeSectionOut = Annotated[
    CategoryGridSectionOut | ProductShelfSectionOut,
    Field(discriminator="type"),
]


=======
class HomeSectionOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable section id, e.g. 'top_rated'.")
    type: str = Field(description="Section kind for the client layout.")
    title: str = Field(description="Localized section title.")
    items: list[CategoryOut | ProductCardOut]
    next_cursor: str | None = Field(description="Opaque cursor for the next page, or null.")


>>>>>>> 1fd479cb87dbe5bed5fa5de16d93293b1e777d0e
class HomeFeedOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    sections: list[HomeSectionOut]
