import pytest

from app.modules.ingredients.matching import candidate_keys


@pytest.mark.parametrize(
    ("raw", "whole", "components"),
    [
        ("Aqua", "aqua", ()),  # nothing to split
        ("Glycérine", "glycerine", ()),
        ("Aqua (Water)", "aqua water", ("aqua", "water")),
        ("Parfum (Fragrance)", "parfum fragrance", ("parfum", "fragrance")),
        ("Aqua/Water/Eau", "aqua water eau", ("aqua", "water", "eau")),
        ("Parfum/Fragrance", "parfum fragrance", ("parfum", "fragrance")),
        ("Aqua [Eau]", "aqua eau", ("aqua", "eau")),
        ("Tocopherol (Vitamin E)", "tocopherol vitamin e", ("tocopherol", "vitamin e")),
        (
            "Glycerin (Vegetable origin)",
            "glycerin vegetable origin",
            ("glycerin", "vegetable origin"),
        ),
        ("Aqua (Aqua)", "aqua aqua", ("aqua",)),  # duplicates collapse
        ("", "", ()),
        ("()", "", ()),
    ],
)
def test_candidate_keys(raw: str, whole: str, components: tuple[str, ...]) -> None:
    candidates = candidate_keys(raw)
    assert candidates.whole == whole
    assert candidates.components == components


def test_single_character_components_are_ignored() -> None:
    # "E" alone would match far too much; parts need at least two characters.
    assert candidate_keys("Vitamin (E)").components == ("vitamin",)


def test_all_keys_never_contains_the_empty_string() -> None:
    assert candidate_keys("").all_keys() == set()
    assert candidate_keys("Aqua (Water)").all_keys() == {"aqua water", "aqua", "water"}
