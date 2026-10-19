"""Text normalization for product-name search (lowercase, no accents, no punctuation)."""

import re
import unicodedata

_NON_WORD = re.compile(r"[^\w\s]")
_SPACES = re.compile(r"\s+")


def normalize_name(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPACES.sub(" ", _NON_WORD.sub(" ", no_accents)).strip()
