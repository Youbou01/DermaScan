"""Enums owned by the reviews module."""

from enum import StrEnum


class ReviewSource(StrEnum):
    """Origin of a product review."""

    APP = "app"
    REDDIT = "reddit"


class ReviewCacheStatus(StrEnum):
    """Freshness state of cached external review fetches."""

    FRESH = "fresh"
    STALE = "stale"
    FAILED = "failed"
