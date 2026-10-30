from enum import StrEnum


class ProductSource(StrEnum):
    """Where a product row came from."""

    OPEN_BEAUTY_FACTS = "open_beauty_facts"
    SCRAPE = "scrape"
    USER_PHOTO = "user_photo"
    MANUAL = "manual"


class EnrichmentStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class ImageStatus(StrEnum):
    NONE = "none"
    CANDIDATE = "candidate"
    PROCESSED = "processed"
    FAILED = "failed"
