from app.core.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    resolve_locale,
    resolve_product_name,
)


def test_supported_locales_includes_arabic() -> None:
    assert "ar" in SUPPORTED_LOCALES
    assert "en" in SUPPORTED_LOCALES
    assert "fr" in SUPPORTED_LOCALES
    assert DEFAULT_LOCALE == "en"


def test_resolve_locale_handles_arabic() -> None:
    assert resolve_locale("ar") == "ar"
    assert resolve_locale("ar-TN,ar;q=0.9,fr;q=0.8") == "ar"
    assert resolve_locale("fr-FR,fr;q=0.9,ar;q=0.8") == "fr"
    assert resolve_locale("de-DE,de;q=0.9") == "en"


def test_resolve_product_name_fallback_chain() -> None:
    original = "Gel Nettoyant Purifiant"
    name_i18n = {
        "en": "Purifying Cleansing Gel",
        "fr": "Gel Nettoyant Purifiant",
        "ar": "جل منظف منقي",
    }

    # 1. Exact match for requested locale
    assert resolve_product_name(original, name_i18n, "ar") == "جل منظف منقي"
    assert resolve_product_name(original, name_i18n, "fr") == "Gel Nettoyant Purifiant"
    assert resolve_product_name(original, name_i18n, "en") == "Purifying Cleansing Gel"

    # 2. Requested locale missing -> falls back to "en"
    partial_i18n = {"en": "Purifying Cleansing Gel", "fr": "Gel Nettoyant"}
    assert resolve_product_name(original, partial_i18n, "ar") == "Purifying Cleansing Gel"

    # 3. Both requested and "en" missing -> falls back to original name
    fr_only_i18n = {"fr": "Gel Nettoyant"}
    assert resolve_product_name(original, fr_only_i18n, "ar") == original

    # 4. None / empty name_i18n -> falls back to original name
    assert resolve_product_name(original, None, "ar") == original
    assert resolve_product_name(original, {}, "ar") == original
