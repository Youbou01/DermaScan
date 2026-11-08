from pydantic import BaseModel, ConfigDict, Field


class SetCuratedRatingInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    rating: float = Field(
        ge=0.0, le=10.0, description="Rating from 0.0 to 10.0 (10 = least concern)"
    )
    summary: str | None = Field(default=None, description="One-sentence plain language summary")
    concern_note: str | None = Field(
        default=None, description="Plain language concern rationale if flagged"
    )


class ScrapeUrlsInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    urls: list[str] = Field(min_length=1, max_length=500)
    site_config: str | None = None


class ScrapeSitemapInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    sitemap_url: str
    site_config: str | None = None
    url_pattern: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class ObfRunInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    barcodes: list[str] | None = None
    limit: int = Field(default=50, ge=1, le=500)
