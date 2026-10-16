"""Shared domain vocabulary (the "shared kernel").

`RiskLevel` is used by ingredients (their rating), scoring (the algorithm input)
and catalog (a product's band). It lives here so no module has to import another
module just to share a word.
"""

from enum import StrEnum


class RiskLevel(StrEnum):
    """Semantic concern level. The API returns this; the mobile app maps it to
    colour + icon + label (never colour alone). UNKNOWN is never treated as safe."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"
