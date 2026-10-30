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
