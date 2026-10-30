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


def test_multilingual_prefixes() -> None:
    assert texts("Zutaten: Aqua, Glycerin") == ["Aqua", "Glycerin"]
    assert texts("Inhaltsstoffe: Aqua, Glycerin") == ["Aqua", "Glycerin"]
    assert texts("Ingredientes: Aqua, Glycerin") == ["Aqua", "Glycerin"]
    assert texts("Ingredienti: Aqua, Glycerin") == ["Aqua", "Glycerin"]
    assert texts("المكونات: ماء, جلسرين") == ["ماء", "جلسرin".replace("in", "ين")]
    assert texts("Ingredients (INCI): Aqua, Glycerin") == ["Aqua", "Glycerin"]


def test_extended_separators_dash_slash_dot() -> None:
    # " - " space dash space
    assert texts("Aqua - Glycerin - Parfum") == ["Aqua", "Glycerin", "Parfum"]
    # 1,2-Hexanediol chemical hyphen preserved
    assert texts("Aqua, 1,2-Hexanediol, Glycerin") == ["Aqua", "1,2-Hexanediol", "Glycerin"]
    # " / " space slash space
    assert texts("Aqua / Glycerin / Parfum") == ["Aqua", "Glycerin", "Parfum"]
    # parenthetical clause with slash preserved
    assert texts("Aqua (Water / Eau), Glycerin") == ["Aqua (Water / Eau)", "Glycerin"]
    # "." followed by capital letter
    assert texts("Aqua. Glycerin. Alcohol Denat.") == ["Aqua", "Glycerin", "Alcohol Denat"]


def test_multi_language_block_selection() -> None:
    raw = "Ingredients: Aqua, Glycerin, Parfum. Ingrédients: Eau, Glycérine, Parfum."
    fr_items = [i.text for i in parse_ingredient_label(raw, preferred_lang="fr")]
    assert "Eau" in fr_items or "Glycérine" in fr_items

    en_items = [i.text for i in parse_ingredient_label(raw, preferred_lang="en")]
    assert "Aqua" in en_items


def test_suspicion_detector_flags_anomalies() -> None:
    from app.modules.ingredients.parser import looks_like_ingredient_list

    # Clean list is not suspicious
    clean = parse_ingredient_label("Aqua, Glycerin, Niacinamide, Tocopherol")
    susp = looks_like_ingredient_list(clean)
    assert not susp.is_suspicious
    assert susp.reasons == []

    # Fewer than 2 items
    one_item = parse_ingredient_label("Aqua")
    susp_one = looks_like_ingredient_list(one_item)
    assert susp_one.is_suspicious
    assert "fewer_than_2_items" in susp_one.reasons

    # Marketing sentence
    marketing = parse_ingredient_label("Aqua, Apply morning and evening on clean face, Glycerin")
    susp_mkt = looks_like_ingredient_list(marketing)
    assert susp_mkt.is_suspicious
    assert "contains_marketing_or_instruction_sentences" in susp_mkt.reasons

    # French instruction
    fr_warn = parse_ingredient_label("Aqua, Tenir hors de portée des enfants, Parfum")
    susp_fr = looks_like_ingredient_list(fr_warn)
    assert susp_fr.is_suspicious
    assert "contains_marketing_or_instruction_sentences" in susp_fr.reasons

    # Spanish modo de empleo
    es_usage = parse_ingredient_label(
        "SPRAY PROTECTOR SOLAR SPF 50 KIDS. "
        "MODO DE EMPLEO: Producto para uso corporal. Agitar antes de usar."
    )
    susp_es = looks_like_ingredient_list(es_usage)
    assert susp_es.is_suspicious

    # Excessive digits
    digits_label = parse_ingredient_label("1234567890123, 9876543210987, 5432109876543")
    susp_digits = looks_like_ingredient_list(digits_label)
    assert susp_digits.is_suspicious
    assert "excessive_digits" in susp_digits.reasons
