import pytest

from app.modules.catalog.search_text import normalize_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Crème Hydratante", "creme hydratante"),
        ("L'Oréal  Paris", "l oreal paris"),
        ("  CeraVe® Gel-Cleanser ", "cerave gel cleanser"),
        ("", ""),
        ("!!!", ""),
    ],
)
def test_normalize_name(raw: str, expected: str) -> None:
    assert normalize_name(raw) == expected
