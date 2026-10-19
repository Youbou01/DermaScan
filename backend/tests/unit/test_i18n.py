import pytest

from app.core.i18n import resolve_locale


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "en"),
        ("", "en"),
        ("fr", "fr"),
        ("FR", "fr"),
        ("fr-FR,fr;q=0.9,en;q=0.8", "fr"),
        ("en-US,en;q=0.9,fr;q=0.8", "en"),
        ("en;q=0.5,fr;q=0.9", "fr"),  # quality beats order
        ("de,fr;q=0.5", "fr"),  # first unsupported language is skipped
        ("de", "en"),
        ("ar", "en"),  # not supported yet: falls back until "ar" is added
        ("fr;q=0,en", "en"),  # q=0 means "not acceptable"
        ("*", "en"),
        ("fr;q=abc", "en"),  # malformed quality is ignored, never an error
        ("!!!;;;,,", "en"),
    ],
)
def test_resolve_locale(header: str | None, expected: str) -> None:
    assert resolve_locale(header) == expected
