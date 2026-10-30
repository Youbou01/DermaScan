from enum import StrEnum


class RawProductSource(StrEnum):
    OPEN_BEAUTY_FACTS = "open_beauty_facts"
    SCRAPE = "scrape"
    USER_PHOTO = "user_photo"
    MANUAL = "manual"


class QuarantineStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
