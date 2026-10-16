from enum import StrEnum


class ProductSource(StrEnum):
    """Where a product row came from. Adding a source needs a migration (on purpose)."""

    OPEN_BEAUTY_FACTS = "open_beauty_facts"
    MANUAL = "manual"
