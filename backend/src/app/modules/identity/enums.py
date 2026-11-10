from enum import StrEnum


class SkinType(StrEnum):
    """Self-declared skin type stored on the user profile."""

    NORMAL = "normal"
    DRY = "dry"
    OILY = "oily"
    COMBINATION = "combination"
    SENSITIVE = "sensitive"


class AlertCode(StrEnum):
    """Machine-readable type of a personal risk alert (frozen contract, sprint 2 section 7)."""

    PREGNANCY_CONTRAINDICATION = "pregnancy_contraindication"
    ALLERGY_MATCH = "allergy_match"
    BLACKLISTED = "blacklisted"
    SKIN_TYPE_MISMATCH = "skin_type_mismatch"


class AlertSeverity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"


class Verdict(StrEnum):
    SUITABLE = "suitable"
    CAUTION = "caution"
    AVOID = "avoid"
