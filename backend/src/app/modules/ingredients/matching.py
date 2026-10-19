"""Which strings do we look up for one label item? Pure function.

The label says "Aqua (Water)", but our dictionary may only know "aqua" and "water" as
separate names. Instead of forcing curators to enter every "X (Y)" spelling, we also try
the parts. Matching is ALWAYS exact on normalized names, never fuzzy (see ADR-0009).
"""

import re
from dataclasses import dataclass

from app.modules.ingredients.normalizer import normalize

_BRACKETED = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]")
_MIN_COMPONENT_LENGTH = 2


@dataclass(frozen=True, slots=True)
class Candidates:
    whole: str  # the normalized item; "" when the item has no letters or digits
    components: tuple[str, ...]  # normalized parts, without duplicates and without `whole`

    def all_keys(self) -> set[str]:
        return {key for key in (self.whole, *self.components) if key}


def candidate_keys(raw_text: str) -> Candidates:
    """
    >>> candidate_keys("Aqua (Water)")
    Candidates(whole='aqua water', components=('aqua', 'water'))
    """
    whole = normalize(raw_text)

    inside = [group for pair in _BRACKETED.findall(raw_text) for group in pair if group]
    outside = _BRACKETED.sub(" ", raw_text)

    components: list[str] = []
    for segment in (outside, *inside):
        for part in segment.split("/"):
            key = normalize(part)
            if len(key) >= _MIN_COMPONENT_LENGTH and key != whole and key not in components:
                components.append(key)

    # Without brackets or slashes the only "component" would be the whole item itself.
    return Candidates(whole=whole, components=tuple(components))
