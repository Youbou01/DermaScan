import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RiskLevel


class ProductSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    barcode: str = Field(description="GTIN-13.")
    name: str
    brand: str | None
    image_url: str | None
    score: int | None = Field(description="0-100, or null when the product is not scored.")
    score_band: RiskLevel = Field(description="'unknown' means insufficient data, NOT safe.")
