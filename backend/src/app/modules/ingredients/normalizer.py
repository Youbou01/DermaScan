"""Text normalization used to compare ingredient names. Pure function.

The SAME function must be used when storing an alias (`ingredient_alias.normalized_alias`)
and when looking one up. If the two ever disagree, matching silently breaks, so there is
exactly one implementation and everybody imports it from this module's public interface.
"""

import re
import unicodedata

_NON_WORD = re.compile(r"[\W_]+")  # anything that is not a letter or digit (any script)


def normalize(text: str) -> str:
    """Lowercase, remove accents, turn punctuation into single spaces.

    >>> normalize("Glycérine")
    'glycerine'
    >>> normalize("Aqua (Water)")
    'aqua water'

    Letters of any script survive (Arabic works too); only marks and punctuation go.
    Returns "" when nothing but punctuation is left: callers must handle that.
    """
    decomposed = unicodedata.normalize("NFKD", text)  # "é" -> "e" + combining accent; "ﬁ" -> "fi"
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    # casefold() is a stronger lower(): "ß" -> "ss". The ligatures are not decomposed by NFKD.
    folded = without_marks.casefold().replace("œ", "oe").replace("æ", "ae")
    return _NON_WORD.sub(" ", folded).strip()
