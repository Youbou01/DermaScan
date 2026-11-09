from enum import StrEnum


class SkinType(StrEnum):
    """Self-declared skin type stored on the user profile."""

    NORMAL = "normal"
    DRY = "dry"
    OILY = "oily"
    COMBINATION = "combination"
    SENSITIVE = "sensitive"
