import pytest

from app.core.i18n import pick_translation, resolve_locale


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "en"),
        ("", "en"),
        ("fr", "fr"),
        ("FR", "fr"),
        ("fr-FR,fr;q=0.9,en;q=0.8", "fr"),
        ("fr-TN", "fr"),  # region subtag ignored
        ("fr-CA,en;q=0.8", "fr"),
        ("en-US,en;q=0.9,fr;q=0.8", "en"),
        ("en;q=0.5,fr;q=0.9", "fr"),  # quality beats order
        ("de,fr;q=0.5", "fr"),  # first unsupported language is skipped
        ("de", "en"),
        ("es", "en"),  # unsupported language falls back to en
        ("ar", "ar"),  # supported optional locale per ADR-0016
        ("fr;q=0,en", "en"),  # q=0 means "not acceptable"
        ("*", "en"),
        ("fr;q=abc", "en"),  # malformed quality is ignored, never an error
        ("!!!;;;,,", "en"),
    ],
)
def test_resolve_locale(header: str | None, expected: str) -> None:
    assert resolve_locale(header) == expected


@pytest.mark.parametrize(
    ("translations", "locale", "expected"),
    [
        ({"en": "Moisturizer", "fr": "Hydratant"}, "fr", "Hydratant"),
        ({"en": "Moisturizer", "fr": "Hydratant"}, "en", "Moisturizer"),
        ({"en": "Moisturizer"}, "fr", "Moisturizer"),  # missing locale -> English
        ({"fr": "Hydratant"}, "en", "Hydratant"),  # no English -> any available
        ({"fr": "Hydratant"}, "de", "Hydratant"),
        ({}, "fr", None),
        ({"en": "Restricted."}, "fr", "Restricted."),
    ],
)
def test_pick_translation(translations: dict[str, str], locale: str, expected: str | None) -> None:
    assert pick_translation(translations, locale) == expected
