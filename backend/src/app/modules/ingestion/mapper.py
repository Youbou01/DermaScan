from collections.abc import Sequence

OBF_CATEGORY_MAP: dict[str, str] = {
    "en:moisturizers": "moisturizer",
    "en:face-creams": "moisturizer",
    "en:creams": "moisturizer",
    "en:cleansers": "cleanser",
    "en:face-cleansers": "cleanser",
    "en:gels": "cleanser",
    "en:serums": "serum",
    "en:face-serums": "serum",
    "en:sunscreens": "sunscreen",
    "en:sun-protections": "sunscreen",
    "en:exfoliants": "exfoliant",
    "en:scrubs": "exfoliant",
    "en:toners": "toner",
    "en:face-toners": "toner",
    "en:masks": "mask",
    "en:face-masks": "mask",
}


def resolve_category_slug(categories_tags: Sequence[str]) -> str:
    """Task E3: Maps OBF category tags to our standardized slugs with safe fallback."""
    for tag in categories_tags:
        if tag in OBF_CATEGORY_MAP:
            return OBF_CATEGORY_MAP[tag]
        for obf_key, slug in OBF_CATEGORY_MAP.items():
            if obf_key in tag.lower():
                return slug
    return "moisturizer"
