from enum import StrEnum


class RatingSource(StrEnum):
    REGULATORY = "regulatory"
    CURATED = "curated"
    AI = "ai"
    UNRATED = "unrated"


class ReviewStatus(StrEnum):
    AUTO = "auto"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"


class AliasSource(StrEnum):
    SEED = "seed"
    COSING = "cosing"
    TAXONOMY = "taxonomy"
    AI = "ai"
    MANUAL = "manual"
