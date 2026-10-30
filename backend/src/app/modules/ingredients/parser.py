"""Splits the raw ingredient text printed on a label into an ordered list. Pure function.

Labels list ingredients by decreasing amount, so ORDER IS DATA: position 1 is the main
ingredient. The parser never reorders or drops duplicates.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

# Typographic characters are written as escapes on purpose: they look identical to "-" or ","
# on screen. \u2013 en dash, \u2014 em dash, \u2212 minus sign, \uff0c / \uff1b full-width , ;
_DASHES = "\u2013\u2014"

_PREFIX_WORDS = (
    r"ingredients?|ingr[eé]dients?|ingredientes?|ingredienti|zutaten|inhaltsstoffe|composition|inci"
    r"|المكونات|مكونات"
)

_PREFIX = re.compile(
    r"^\s*(?:" + _PREFIX_WORDS + r")\s*(?:\([^)]*\))?\s*(?:[:\-" + _DASHES + r"]|\s)\s*",
    re.IGNORECASE,
)

_BLOCK_PREFIX = re.compile(
    r"(?:^|[\n./;]|\s[-\u2013\u2014]\s)\s*(?P<tag>"
    + _PREFIX_WORDS
    + r")\s*(?:\([^)]*\))?\s*[:\-"
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
_CHEMICAL_COMMA = re.compile(r"(?<=\d),(?=\d+(?:,\d+)*-[A-Za-z])")
_CHEMICAL_PLACEHOLDER = "\u0000"

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

_MARKETING_SENTENCES = re.compile(
    r"\b(?:"
    # English
    r"apply\s+(?:morning|evening|daily|to|generously|evenly)|directions\s+for\s+use|how\s+to\s+use"
    r"|keep\s+out\s+of\s+reach|for\s+external\s+use\s+only|avoid\s+contact\s+with\s+eyes"
    r"|store\s+in\s+a\s+cool|dermatologically\s+tested|made\s+in"
    # French
    r"|appliquer\s+(?:matin|soir|quotidiennement|g[eé]n[eé]reusement|sur)"
    r"|mode\s+d['\s]emploi|conseils\s+d['\s]utilisation|tenir\s+hors\s+de\s+port[eé]e"
    r"|usage\s+externe\s+uniquement|[eé]viter\s+le\s+contact\s+avec\s+les\s+yeux"
    r"|fabriqu[eé]\s+en|test[eé]\s+dermatologiquement"
    # Spanish
    r"|modo\s+de\s+empleo|agitar\s+antes\s+de\s+usar|mantener\s+fuera\s+del\s+alcance"
    r"|evitar\s+el\s+contacto|uso\s+corporal|beneficios|consideraciones"
    # German
    r"|augenkontakt\s+vermeiden|dermatologisch\s+best[aä]tigt|f[uü]r\s+k[oö]rper"
    r"|vor\s+gebrauch\s+sch[uü]tteln|sanft\s+&\s+sicher|toilettenpapier"
    # Italian
    r"|agitare\s+bene|istruzioni|evitare\s+il\s+contatto|applicare\s+da"
    # Turkish
    r"|kullanma\s+talimat|uzak\s+tutunuz"
    r")\b",
    re.IGNORECASE,
)

_COMMON_INCI_TOKENS = {
    "aqua",
    "water",
    "eau",
    "glycerin",
    "glyzerin",
    "alcohol",
    "acid",
    "oil",
    "extract",
    "glycol",
    "sulfate",
    "panthenol",
    "tocopherol",
    "stearate",
    "chloride",
    "oxide",
    "dimethicone",
    "parfum",
    "fragrance",
    "limonene",
    "linalool",
}


@dataclass(frozen=True, slots=True)
class ParsedIngredient:
    position: int  # 1-based, as printed on the label
    text: str  # the item as printed, without bullets, footnote stars or percentage
    percentage: float | None  # only when the label states it (rare)


@dataclass(frozen=True, slots=True)
class Suspicion:
    is_suspicious: bool
    reasons: list[str]


def _score_block(block: str, tag: str, preferred_lang: str | None) -> int:
    score = 0
    tag_lower = tag.lower()
    if preferred_lang:
        pref = preferred_lang.lower()
        if (
            (pref == "fr" and ("ingr[eé]dient" in tag_lower or tag_lower.startswith("ingréd")))
            or (pref == "en" and tag_lower.startswith("ingredient"))
            or (pref == "de" and tag_lower in ("zutaten", "inhaltsstoffe"))
        ):
            score += 10

    words = set(re.findall(r"\b[a-zA-Z]{3,}\b", block.lower()))
    common_matches = len(words & _COMMON_INCI_TOKENS)
    score += common_matches * 2
    score += min(len(block.split(",")), 30)
    return score


def _extract_best_language_block(text: str, preferred_lang: str | None) -> str:
    matches = list(_BLOCK_PREFIX.finditer(text))
    if len(matches) < 2:
        return text

    blocks: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        tag = match.group("tag")
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block_text = text[start:end].strip()
        if block_text:
            blocks.append((block_text, tag))

    if not blocks:
        return text

    best_block, _ = max(blocks, key=lambda item: _score_block(item[0], item[1], preferred_lang))
    return best_block


def _replace_extended_separators(text: str) -> str:
    """Bracket-aware replacement for ' - ', ' / ', and '.' followed by capital letter."""
    result: list[str] = []
    depth = 0
    length = len(text)
    i = 0

    while i < length:
        ch = text[i]
        if ch in _OPENING:
            depth += 1
            result.append(ch)
            i += 1
            continue
        if ch in _CLOSING:
            depth = max(depth - 1, 0)
            result.append(ch)
            i += 1
            continue

        if depth == 0:
            # Check for ' - ' (space dash space)
            if (
                i + 2 < length
                and text[i] == " "
                and text[i + 1] in ("-", "\u2013", "\u2014")
                and text[i + 2] == " "
            ):
                result.append(", ")
                i += 3
                continue

            # Check for ' / ' (space slash space)
            if i + 2 < length and text[i] == " " and text[i + 1] == "/" and text[i + 2] == " ":
                result.append(", ")
                i += 3
                continue

            # Check for '.' followed by space and capital letter
            if ch == "." and i + 1 < length:
                rest = text[i + 1 :]
                match_space = re.match(r"^\s+([A-Z\u00C0-\u00DC])", rest)
                if match_space:
                    result.append(", ")
                    i += 1 + len(match_space.group(0)) - 1
                    result.append(match_space.group(1))
                    i += 1
                    continue

        result.append(ch)
        i += 1

    return "".join(result)


def parse_ingredient_label(raw: str, preferred_lang: str | None = None) -> list[ParsedIngredient]:
    """Turn a label text into ordered ingredients. Never raises; returns [] for junk."""
    text = unicodedata.normalize("NFKC", raw)
    text = _extract_best_language_block(text, preferred_lang)
    text = _PREFIX.sub("", text, count=1)

    stop = _STOP_MARKER.search(text)
    if stop:
        text = text[: stop.start()]

    text = text.translate(_SEPARATORS)
    text = _replace_extended_separators(text)

    # Newlines: when the text has commas, a newline is just line wrapping inside the list;
    # without any comma, the text is one-ingredient-per-line.
    text = text.replace("\r", "\n")
    text = text.replace("\n", " " if "," in text else ",")
    text = _CHEMICAL_COMMA.sub(_CHEMICAL_PLACEHOLDER, text)

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
    item = item.replace(_CHEMICAL_PLACEHOLDER, ",")
    if not any(char.isalnum() for char in item):
        return "", None
    return item, percentage


def looks_like_ingredient_list(parsed: Sequence[ParsedIngredient]) -> Suspicion:
    """Pure function inspecting parsed ingredient list for signs of junk or marketing text."""
    reasons: list[str] = []

    if len(parsed) < 2:
        reasons.append("fewer_than_2_items")

    total_chars = 0
    digit_chars = 0
    has_sentence = False
    has_long_item = False

    for item in parsed:
        total_chars += len(item.text)
        digit_chars += sum(1 for c in item.text if c.isdigit())

        if len(item.text) > 120 and not has_long_item:
            has_long_item = True
            reasons.append("item_exceeds_120_chars")

        if not has_sentence and _MARKETING_SENTENCES.search(item.text):
            has_sentence = True
            reasons.append("contains_marketing_or_instruction_sentences")

    if total_chars > 0 and (digit_chars / total_chars) > 0.40:
        reasons.append("excessive_digits")

    return Suspicion(is_suspicious=len(reasons) > 0, reasons=reasons)
