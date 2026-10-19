"""Locale resolution. Supported languages are listed in ONE place: we'll add "ar" here when
Arabic content exists (and nowhere else)."""

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "fr")


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
