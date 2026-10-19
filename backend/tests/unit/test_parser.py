import pytest

from app.modules.ingredients.parser import ParsedIngredient, parse_ingredient_label


def texts(raw: str) -> list[str]:
    return [item.text for item in parse_ingredient_label(raw)]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # basics
        ("Aqua, Glycerin, Parfum", ["Aqua", "Glycerin", "Parfum"]),
        ("Aqua,Glycerin ,  Parfum  ", ["Aqua", "Glycerin", "Parfum"]),
        ("Aqua, Glycerin, Parfum.", ["Aqua", "Glycerin", "Parfum"]),  # final period
        ("AQUA, GLYCERIN", ["AQUA", "GLYCERIN"]),  # keeps the printed case
        # prefixes in both languages
        ("Ingredients: Aqua, Glycerin", ["Aqua", "Glycerin"]),
        ("INGREDIENTS: AQUA, GLYCERIN", ["AQUA", "GLYCERIN"]),
        ("Ingrédients : Eau, Glycérine", ["Eau", "Glycérine"]),
        ("Ingrédients: Eau, Glycérine", ["Eau", "Glycérine"]),
        ("Ingredients (INCI): Aqua, Glycerin", ["Aqua", "Glycerin"]),
        ("Composition : Eau, Glycérine", ["Eau", "Glycérine"]),
        # other separators
        ("Aqua; Glycerin; Parfum", ["Aqua", "Glycerin", "Parfum"]),
        ("• Aqua • Glycerin • Parfum", ["Aqua", "Glycerin", "Parfum"]),
        ("Aqua | Glycerin | Parfum", ["Aqua", "Glycerin", "Parfum"]),
        ("Aqua، Glycerin", ["Aqua", "Glycerin"]),  # Arabic comma
        ("Aqua\uff0cGlycerin", ["Aqua", "Glycerin"]),  # full-width comma (U+FF0C)
        # commas inside brackets do not split
        ("Parfum (Linalool, Limonene), Aqua", ["Parfum (Linalool, Limonene)", "Aqua"]),
        ("Aqua [Water, Eau], Glycerin", ["Aqua [Water, Eau]", "Glycerin"]),
        ("Aqua (Water), Parfum (Fragrance)", ["Aqua (Water)", "Parfum (Fragrance)"]),
        # unbalanced bracket: do not swallow the rest of the label
        ("Aqua (Water, Glycerin, Parfum", ["Aqua (Water", "Glycerin", "Parfum"]),
        ("Aqua, Glycerin), Parfum", ["Aqua", "Glycerin)", "Parfum"]),
        # footnote stars and bullets
        ("Aloe Barbadensis Leaf Juice*, Aqua", ["Aloe Barbadensis Leaf Juice", "Aqua"]),
        ("Aqua**, *Glycerin", ["Aqua", "Glycerin"]),
        ("- Aqua, - Glycerin", ["Aqua", "Glycerin"]),
        # empty items are dropped, order of the others is kept
        ("Aqua,, Glycerin, ,", ["Aqua", "Glycerin"]),
        ("Aqua, 123, Glycerin", ["Aqua", "123", "Glycerin"]),  # digits are not junk (CI 77891)
        ("Aqua, ..., Glycerin", ["Aqua", "Glycerin"]),
        # "may contain" and "+/-" sections are not part of the list
        ("Aqua, Glycerin. May contain: Nuts", ["Aqua", "Glycerin"]),
        ("Aqua, Glycerin, may also contain traces of milk", ["Aqua", "Glycerin"]),
        ("Eau, Glycérine. Peut contenir des traces de lait", ["Eau", "Glycérine"]),
        ("Aqua, Glycerin, +/- CI 77891, CI 77491", ["Aqua", "Glycerin"]),
        ("Aqua, Glycerin [+/- CI 77891]", ["Aqua", "Glycerin"]),
        ("Aqua, Glycerin, +/\u2212 CI 77891", ["Aqua", "Glycerin"]),  # typographic minus sign
        ("Aqua, Glycerin, +/\u2013 CI 77891", ["Aqua", "Glycerin"]),  # en dash
        # a name that merely contains similar letters is not a marker
        ("Aqua, Mayonnaise Extract", ["Aqua", "Mayonnaise Extract"]),
        # whitespace oddities
        ("Aqua,\u00a0Glycerin", ["Aqua", "Glycerin"]),  # non-breaking space
        ("Aqua,\tGlycerin", ["Aqua", "Glycerin"]),
        ("Sodium   Lauryl    Sulfate", ["Sodium Lauryl Sulfate"]),
        # junk
        ("", []),
        ("   ", []),
        (",,,", []),
        ("Ingredients:", []),
        ("May contain nuts", []),
    ],
)
def test_parse_texts(raw: str, expected: list[str]) -> None:
    assert texts(raw) == expected


def test_positions_are_one_based_and_contiguous_after_dropping_empties() -> None:
    items = parse_ingredient_label("Aqua,, Glycerin, ,Parfum")
    assert [(i.position, i.text) for i in items] == [(1, "Aqua"), (2, "Glycerin"), (3, "Parfum")]


def test_duplicates_are_kept_in_order() -> None:
    assert texts("Aqua, Glycerin, Aqua") == ["Aqua", "Glycerin", "Aqua"]


@pytest.mark.parametrize(
    ("raw", "text", "percentage"),
    [
        ("Glycerin 5%", "Glycerin", 5.0),
        ("Glycerin 5 %", "Glycerin", 5.0),
        ("Parfum (0.5%)", "Parfum", 0.5),
        ("Parfum (0,5 %)", "Parfum", 0.5),  # French decimal comma inside brackets
        ("70% Aqua", "Aqua", 70.0),
        ("Aqua", "Aqua", None),
    ],
)
def test_percentages_are_extracted_not_left_in_the_name(
    raw: str, text: str, percentage: float | None
) -> None:
    assert parse_ingredient_label(raw) == [ParsedIngredient(1, text, percentage)]


def test_a_percentage_does_not_break_the_split() -> None:
    items = parse_ingredient_label("Aqua 70%, Glycerin 5%, Parfum")
    assert [(i.text, i.percentage) for i in items] == [
        ("Aqua", 70.0),
        ("Glycerin", 5.0),
        ("Parfum", None),
    ]


def test_newlines_are_wrapping_when_the_label_uses_commas() -> None:
    raw = "Aqua, Sodium Lauryl\nSulfate, Glycerin,\nParfum"
    assert texts(raw) == ["Aqua", "Sodium Lauryl Sulfate", "Glycerin", "Parfum"]


def test_newlines_separate_items_when_there_are_no_commas() -> None:
    assert texts("Aqua\nGlycerin\r\nParfum") == ["Aqua", "Glycerin", "Parfum"]


def test_a_realistic_french_label() -> None:
    raw = (
        "Ingrédients : Aqua (Eau), Glycerin, Cetearyl Alcohol, Parfum (Fragrance), "
        "Phenoxyethanol, Tocopherol*, Citric Acid. +/- CI 77891"
    )
    assert texts(raw) == [
        "Aqua (Eau)",
        "Glycerin",
        "Cetearyl Alcohol",
        "Parfum (Fragrance)",
        "Phenoxyethanol",
        "Tocopherol",
        "Citric Acid",
    ]


def test_parsing_never_raises_on_hostile_input() -> None:
    nasty = ["(" * 5000, ")" * 5000, "," * 5000, "\x00\x01\x02", "💥" * 100, "Aqua," * 3000]
    for raw in nasty:
        assert isinstance(parse_ingredient_label(raw), list)
