"""Splits the raw ingredient text printed on a label into an ordered list. Pure function.

Labels list ingredients by decreasing amount, so ORDER IS DATA: position 1 is the main
ingredient. The parser never reorders or drops duplicates.

Known limitations (documented, not bugs): a label printed in several languages in one text
("Ingredients: ... Ingrédients: ...") yields every list one after the other, and
"(and)" blends like "Glycol Distearate (and) Laureth-4" stay a single item.
"""

import re
import unicodedata
from dataclasses import dataclass

# Typographic characters are written as escapes on purpose: they look identical to "-" or ","
# on screen. \u2013 en dash, \u2014 em dash, \u2212 minus sign, \uff0c / \uff1b full-width , ;
_DASHES = "\u2013\u2014"
_PREFIX = re.compile(
    r"^\s*(?:ingredients?|ingr[eé]dients?|composition|inci)\s*(?:\([^)]*\))?\s*[:\-"
    + _DASHES
    + r"]\s*",
    re.IGNORECASE,
)

# Everything from one of these markers onward is NOT part of the ingredient list:
# "may contain ..." / "peut contenir ..." and the cosmetics convention "+/- CI 77891, ...".
_STOP_MARKER = re.compile(
    r"\bmay\s+(?:also\s+)?contain\b"
    r"|\bmight\s+contain\b"
    r"|\bpeut\s+(?:[eé]galement\s+)?contenir\b"
    r"|\[?\s*\+\s*/\s*[-\u2212\u2013]\s*\]?",
    re.IGNORECASE,
)

_LEADING_PERCENT = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*%\s*")
_TRAILING_PERCENT = re.compile(r"\s*\(?\s*(\d+(?:[.,]\d+)?)\s*%\s*\)?\s*$")

_SEPARATORS = str.maketrans(
    {
        ";": ",",
        "\u2022": ",",  # bullet
        "\u00b7": ",",  # middle dot
        "|": ",",
        "\u060c": ",",  # Arabic comma
        "\u061b": ",",  # Arabic semicolon
        "\uff0c": ",",  # full-width comma
        "\uff1b": ",",  # full-width semicolon
    }
)
_OPENING, _CLOSING = "([{", ")]}"
_STRIPPED_EDGES = " \t.*\u2020\u2021:-" + _DASHES  # \u2020 dagger, \u2021 double dagger


@dataclass(frozen=True, slots=True)
class ParsedIngredient:
    position: int  # 1-based, as printed on the label
    text: str  # the item as printed, without bullets, footnote stars or percentage
    percentage: float | None  # only when the label states it (rare)


def parse_ingredient_label(raw: str) -> list[ParsedIngredient]:
    """Turn a label text into ordered ingredients. Never raises; returns [] for junk."""
    # NFKC: non-breaking spaces become spaces, full-width punctuation becomes ASCII.
    text = unicodedata.normalize("NFKC", raw)
    text = _PREFIX.sub("", text, count=1)

    stop = _STOP_MARKER.search(text)
    if stop:
        text = text[: stop.start()]

    text = text.translate(_SEPARATORS)
    # Newlines: when the text has commas, a newline is just line wrapping inside the list;
    # without any comma, the text is one-ingredient-per-line.
    text = text.replace("\r", "\n")
    text = text.replace("\n", " " if "," in text else ",")

    items: list[ParsedIngredient] = []
    for chunk in _split_top_level(text):
        cleaned, percentage = _clean_item(chunk)
        if cleaned:
            items.append(ParsedIngredient(len(items) + 1, cleaned, percentage))
    return items


def _split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside (), [] or {}: "Parfum (A, B), Aqua" is 2 items."""
    chunks: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char in _OPENING:
            depth += 1
        elif char in _CLOSING:
            depth = max(depth - 1, 0)
        if char == "," and depth == 0:
            chunks.append("".join(current))
            current = []
        else:
            current.append(char)
    chunks.append("".join(current))

    if depth != 0:  # unbalanced brackets (typos, OCR): do not swallow the rest of the label
        return text.split(",")
    return chunks


def _clean_item(chunk: str) -> tuple[str, float | None]:
    item = chunk.strip()
    percentage: float | None = None
    for pattern in (_LEADING_PERCENT, _TRAILING_PERCENT):
        found = pattern.search(item)
        if found:
            percentage = float(found.group(1).replace(",", "."))
            item = pattern.sub("", item, count=1)
    item = re.sub(r"\s+", " ", item.strip(_STRIPPED_EDGES))
    if not any(char.isalnum() for char in item):
        return "", None
    return item, percentage
