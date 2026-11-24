"""Personal library request and response DTOs."""

from pydantic import BaseModel, ConfigDict

from app.core.keyset import Page
from app.modules.catalog.schemas import ProductCardOut

ProductPageOut = Page[ProductCardOut]


class SavedProductStatusOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    saved: bool
