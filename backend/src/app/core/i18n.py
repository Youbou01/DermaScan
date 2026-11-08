"""Locale resolution and translation fallback.

Supported languages are listed in ONE place: add "ar" to `SUPPORTED_LOCALES` when
Arabic content exists (and nowhere else).
"""

from collections.abc import Mapping

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "fr", "ar")


def resolve_locale(accept_language: str | None) -> str:
    """Pick the best supported locale from an `Accept-Language` header value.

    "fr-FR,fr;q=0.9,en;q=0.8" -> "fr". Unsupported, empty or malformed input -> "en".
    Never raises: a weird header must never break a request.
    """
    if not accept_language:
        return DEFAULT_LOCALE

    candidates: list[tuple[float, int, str]] = []  # (-quality, original order, language)
    for order, part in enumerate(accept_language.split(",")):
        tag, *params = part.strip().split(";")
        tag = tag.strip().lower()
        if not tag or tag == "*":
            continue
        quality = 1.0
        for param in params:
            name, _, value = param.strip().partition("=")
            if name.strip().lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        if quality > 0:
            candidates.append((-quality, order, tag.split("-")[0]))

    for _, _, language in sorted(candidates):
        if language in SUPPORTED_LOCALES:
            return language
    return DEFAULT_LOCALE


def pick_translation[T](translations: Mapping[str, T], locale: str) -> T | None:
    """Return text for `locale`, else English, else any available value, else None.

    Pure helper for category names, ingredient rationales, and similar locale maps.
    """
    if locale in translations:
        return translations[locale]
    if DEFAULT_LOCALE in translations:
        return translations[DEFAULT_LOCALE]
    for value in translations.values():
        return value
    return None


def resolve_product_name(
    name: str,
    name_i18n: Mapping[str, str] | None,
    locale: str,
) -> str:
    """Return product name localized for `locale`, else English, else original name."""
    if name_i18n:
        if name_i18n.get(locale):
            return str(name_i18n[locale])
        if name_i18n.get(DEFAULT_LOCALE):
            return str(name_i18n[DEFAULT_LOCALE])
    return name
