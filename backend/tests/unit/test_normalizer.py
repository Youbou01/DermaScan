import pytest

from app.modules.ingredients.normalizer import normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # case
        ("AQUA", "aqua"),
        ("Sodium Lauryl Sulfate", "sodium lauryl sulfate"),
        # French accents and ligatures
        ("Glycérine", "glycerine"),
        ("Huile d'Olive", "huile d olive"),
        ("Extrait de cœur de palmier", "extrait de coeur de palmier"),
        ("Cire d'abeille — Œstrogène", "cire d abeille oestrogene"),
        ("Acide Hyaluronique", "acide hyaluronique"),
        ("Eau", "eau"),
        # punctuation, brackets, slashes become single spaces
        ("Aqua (Water)", "aqua water"),
        ("Parfum/Fragrance", "parfum fragrance"),
        ("PEG-40 Hydrogenated Castor Oil", "peg 40 hydrogenated castor oil"),
        ("  Tocopheryl   Acetate  ", "tocopheryl acetate"),
        ("CI 77891", "ci 77891"),
        ("CI77891", "ci77891"),  # not the same key as "CI 77891": needs its own alias
        ("E330", "e330"),
        ("Vitamin B3 (Niacinamide)", "vitamin b3 niacinamide"),
        # typographic variants of the same character
        ("L\u2019Oréal", "l oreal"),  # curly apostrophe (U+2019)
        ("Glycerin\u00a0Stearate", "glycerin stearate"),  # non-breaking space
        ("ﬁlm", "film"),  # ligature
        ("Straße", "strasse"),
        # other scripts keep their letters (Arabic is planned)
        ("ماء", "ماء"),
        ("مَاء", "ماء"),  # diacritics removed
        # nothing left
        ("", ""),
        ("   ", ""),
        ("()", ""),
        (" - / . ", ""),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["Glycérine", "Aqua (Water)", "CI 77891", "L\u2019Oréal", "Extrait de cœur", "ماء", "", "A--B"],
)
def test_normalize_is_idempotent(raw: str) -> None:
    """Normalizing twice must change nothing, otherwise stored and queried keys can drift."""
    once = normalize(raw)
    assert normalize(once) == once


def test_accented_and_plain_spellings_share_one_key() -> None:
    assert normalize("Glycérine") == normalize("glycerine") == normalize("GLYCERINE")
