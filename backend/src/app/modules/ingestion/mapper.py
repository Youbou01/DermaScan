"""Deterministic Open Beauty Facts product record mapper.

Extracts normalized metadata from raw OBF JSON records with exact category matching,
brand normalization, preferred image selection, and language negotiation.
"""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.gtin import normalize_gtin

OBF_EXACT_CATEGORY_MAP: dict[str, str] = {
    # Face care - Cleanser
    "en:cleansers": "cleanser",
    "en:face-cleansers": "cleanser",
    "en:facial-cleansers": "cleanser",
    "en:cleansing-milks": "cleanser",
    "en:cleansing-gels": "cleanser",
    "en:cleansing-foams": "cleanser",
    "en:micellar-waters": "cleanser",
    "en:cleansing-waters": "cleanser",
    "fr:nettoyants": "cleanser",
    "fr:nettoyants-visage": "cleanser",
    "fr:eaux-micellaires": "cleanser",
    "fr:gels-nettoyants": "cleanser",
    "fr:mousses-nettoyantes": "cleanser",
    # Face care - Toner
    "en:toners": "toner",
    "en:face-toners": "toner",
    "en:facial-toners": "toner",
    "en:astringents": "toner",
    "fr:toniques": "toner",
    "fr:lotions-toniques": "toner",
    # Face care - Serum
    "en:serums": "serum",
    "en:face-serums": "serum",
    "en:facial-serums": "serum",
    "en:skin-serums": "serum",
    "fr:serums": "serum",
    "fr:serums-visage": "serum",
    # Face care - Moisturizer
    "en:moisturizers": "moisturizer",
    "en:face-creams": "moisturizer",
    "en:creams": "moisturizer",
    "en:day-creams": "moisturizer",
    "en:night-creams": "moisturizer",
    "en:facial-moisturizers": "moisturizer",
    "fr:cremes-hydratantes": "moisturizer",
    "fr:cremes-visage": "moisturizer",
    "fr:cremes-de-jour": "moisturizer",
    "fr:cremes-de-nuit": "moisturizer",
    "fr:soins-hydratants": "moisturizer",
    # Face care - Face Mask
    "en:masks": "face-mask",
    "en:face-masks": "face-mask",
    "en:sheet-masks": "face-mask",
    "en:facial-masks": "face-mask",
    "fr:masques": "face-mask",
    "fr:masques-visage": "face-mask",
    "fr:masques-en-tissu": "face-mask",
    # Face care - Exfoliant
    "en:exfoliants": "exfoliant",
    "en:scrubs": "exfoliant",
    "en:facial-scrubs": "exfoliant",
    "en:chemical-exfoliants": "exfoliant",
    "en:peelings": "exfoliant",
    "fr:exfoliants": "exfoliant",
    "fr:gommages": "exfoliant",
    "fr:gommages-visage": "exfoliant",
    "fr:peelings": "exfoliant",
    # Face care - Eye Care
    "en:eye-care": "eye-care",
    "en:eye-creams": "eye-care",
    "en:eye-contour-creams": "eye-care",
    "en:eye-gels": "eye-care",
    "fr:soins-contour-des-yeux": "eye-care",
    "fr:cremes-contour-des-yeux": "eye-care",
    # Sun care - Sunscreen
    "en:sunscreens": "sunscreen",
    "en:sun-protections": "sunscreen",
    "en:face-sunscreens": "sunscreen",
    "en:sun-creams": "sunscreen",
    "en:sun-protection-creams": "sunscreen",
    "fr:cremes-solaires": "sunscreen",
    "fr:protections-solaires": "sunscreen",
    "fr:ecrans-solaires": "sunscreen",
    # Sun care - After-sun
    "en:after-sun": "after-sun",
    "en:after-sun-products": "after-sun",
    "en:after-sun-lotions": "after-sun",
    "fr:apres-soleil": "after-sun",
    "fr:soins-apres-soleil": "after-sun",
    # Body care - Body Lotion
    "en:body-lotions": "body-lotion",
    "en:body-creams": "body-lotion",
    "en:body-milks": "body-lotion",
    "en:body-moisturizers": "body-lotion",
    "fr:laits-corps": "body-lotion",
    "fr:cremes-corps": "body-lotion",
    # Body care - Body Wash
    "en:body-washes": "body-wash",
    "en:shower-gels": "body-wash",
    "en:baths": "body-wash",
    "en:bath-and-shower-gels": "body-wash",
    "fr:gels-douche": "body-wash",
    "fr:savons-liquides": "body-wash",
    # Body care - Hand Care
    "en:hand-creams": "hand-care",
    "en:hand-care": "hand-care",
    "en:hand-lotions": "hand-care",
    "fr:cremes-mains": "hand-care",
    "fr:cremes-pour-les-mains": "hand-care",
    "fr:soins-des-mains": "hand-care",
    # Body care - Deodorant
    "en:deodorants": "deodorant",
    "en:antiperspirants": "deodorant",
    "fr:deodorants": "deodorant",
    "fr:anti-transpirants": "deodorant",
    # Body care - Shaving
    "en:shaving": "shaving",
    "en:shaving-foams": "shaving",
    "en:shaving-creams": "shaving",
    "en:after-shaves": "shaving",
    "fr:rasage": "shaving",
    "fr:mousses-a-raser": "shaving",
    "fr:apres-rasage": "shaving",
    # Body care - Baby Care
    "en:baby-care": "baby-care",
    "en:baby-creams": "baby-care",
    "en:baby-lotions": "baby-care",
    "fr:soins-bebe": "baby-care",
    "fr:cremes-bebe": "baby-care",
    # Lip care
    "en:lip-care": "lip-care",
    "en:lip-balms": "lip-care",
    "en:lipsticks": "lip-care",
    "en:lip-glosses": "lip-care",
    "en:lip-care-products": "lip-care",
    "fr:soins-des-levres": "lip-care",
    "fr:baumes-a-levres": "lip-care",
}


class MappedProduct(BaseModel):
    model_config = ConfigDict(frozen=True)

    barcode: str
    name: str
    name_i18n: dict[str, str] = Field(default_factory=dict)
    brands: list[str] = Field(default_factory=list)
    primary_brand: str | None = None
    category_slug: str | None = None
    unmapped_categories: list[str] = Field(default_factory=list)
    raw_ingredients_text: str = ""
    source_lang: str | None = None
    image_url: str | None = None
    needs_ai: bool = False
    field_provenance: dict[str, Any] = Field(default_factory=dict)


def _clean_brand_token(token: str) -> str:
    cleaned = token.strip()
    if cleaned.lower().startswith(("en:", "fr:")):
        cleaned = cleaned[3:].strip()
    return cleaned


def extract_brands(record: dict[str, Any]) -> tuple[list[str], str | None, str]:
    """Extract ordered non-empty brand tokens and identify primary brand."""
    raw_brands = record.get("brands_tags") or record.get("brands")
    source_key = "brands_tags" if record.get("brands_tags") else "brands"
    brands: list[str] = []
    seen: set[str] = set()

    tokens: list[str] = []
    if isinstance(raw_brands, list):
        for item in raw_brands:
            if isinstance(item, str):
                tokens.extend(item.split(","))
    elif isinstance(raw_brands, str):
        tokens.extend(raw_brands.split(","))

    for tok in tokens:
        cleaned = _clean_brand_token(tok)
        if not cleaned:
            continue
        norm_key = cleaned.lower()
        if norm_key not in seen:
            seen.add(norm_key)
            brands.append(cleaned)

    primary = brands[0] if brands else None
    return brands, primary, source_key


def resolve_category(record: dict[str, Any]) -> tuple[str | None, list[str], str | None]:
    """Match categories strictly against exact OBF tags.

    Returns:
        (matched_slug, unmapped_tags, matched_tag)
    """
    tags_source = record.get("categories_tags")
    hierarchy_source = record.get("categories_hierarchy")

    raw_candidates: list[str] = []
    if isinstance(tags_source, list):
        raw_candidates.extend(str(t).strip() for t in tags_source if t)
    if isinstance(hierarchy_source, list):
        raw_candidates.extend(str(t).strip() for t in hierarchy_source if t)

    unmapped: list[str] = []
    for tag in raw_candidates:
        normalized_tag = tag.lower()
        if normalized_tag in OBF_EXACT_CATEGORY_MAP:
            return OBF_EXACT_CATEGORY_MAP[normalized_tag], unmapped, tag
        if tag not in unmapped:
            unmapped.append(tag)

    return None, unmapped, None


def _is_valid_front_image_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    url_lower = url.lower()
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        return False
    return not ("ingredients_" in url_lower or "nutrition_" in url_lower)


def select_image_url(record: dict[str, Any], lang_pref: str | None) -> tuple[str | None, str]:
    """Select preferred front image URL and avoid ingredients/nutrition photos."""
    selected_images = record.get("selected_images")
    if isinstance(selected_images, dict):
        front = selected_images.get("front")
        if isinstance(front, dict):
            display = front.get("display")
            if isinstance(display, dict):
                candidates: list[tuple[str, str | None]] = []
                if lang_pref and lang_pref in display:
                    candidates.append(
                        (f"selected_images.front.display.{lang_pref}", display.get(lang_pref))
                    )
                for lang_key in ("fr", "en"):
                    if lang_key in display:
                        candidates.append(
                            (f"selected_images.front.display.{lang_key}", display.get(lang_key))
                        )
                for k, v in display.items():
                    candidates.append((f"selected_images.front.display.{k}", v))

                for key_name, candidate in candidates:
                    if candidate and _is_valid_front_image_url(candidate):
                        return candidate, key_name

    front_url = record.get("image_front_url")
    if _is_valid_front_image_url(front_url):
        return str(front_url), "image_front_url"

    generic_url = record.get("image_url")
    if _is_valid_front_image_url(generic_url):
        return str(generic_url), "image_url"

    return None, "none"


def resolve_category_slug(categories_tags: Sequence[str]) -> str | None:
    """Exact tag matching for standardized category slugs. Returns None when unknown."""
    for tag in categories_tags:
        clean = str(tag).strip().lower()
        if clean in OBF_EXACT_CATEGORY_MAP:
            return OBF_EXACT_CATEGORY_MAP[clean]
    return None


def map_obf_record(record: dict[str, Any]) -> MappedProduct:
    """Pure deterministic mapper transforming an OpenBeautyFacts record to MappedProduct."""
    raw_code = str(record.get("code") or record.get("id") or "").strip()
    try:
        barcode = normalize_gtin(raw_code)
    except Exception:
        barcode = raw_code

    record_lang = str(record.get("lang") or "").strip().lower() or None

    name_i18n: dict[str, str] = {}
    for k, v in record.items():
        if k.startswith("product_name_") and isinstance(v, str) and v.strip():
            lang_suffix = k.removeprefix("product_name_").strip().lower()
            if len(lang_suffix) == 2:
                name_i18n[lang_suffix] = v.strip()

    name = ""
    name_source = ""
    if record.get("product_name_fr"):
        name = str(record["product_name_fr"]).strip()
        name_source = "product_name_fr"
    elif record.get("product_name_en"):
        name = str(record["product_name_en"]).strip()
        name_source = "product_name_en"
    elif record_lang and record.get(f"product_name_{record_lang}"):
        name = str(record[f"product_name_{record_lang}"]).strip()
        name_source = f"product_name_{record_lang}"
    elif record.get("product_name"):
        name = str(record["product_name"]).strip()
        name_source = "product_name"

    ingredients_text = ""
    ingredients_source = ""
    source_lang: str | None = None

    if record.get("ingredients_text_fr"):
        ingredients_text = str(record["ingredients_text_fr"]).strip()
        ingredients_source = "ingredients_text_fr"
        source_lang = "fr"
    elif record.get("ingredients_text_en"):
        ingredients_text = str(record["ingredients_text_en"]).strip()
        ingredients_source = "ingredients_text_en"
        source_lang = "en"
    elif record_lang and record.get(f"ingredients_text_{record_lang}"):
        ingredients_text = str(record[f"ingredients_text_{record_lang}"]).strip()
        ingredients_source = f"ingredients_text_{record_lang}"
        source_lang = record_lang
    elif record.get("ingredients_text"):
        ingredients_text = str(record["ingredients_text"]).strip()
        ingredients_source = "ingredients_text"
        source_lang = record_lang or "en"

    brands, primary_brand, brand_source = extract_brands(record)
    category_slug, unmapped_cats, matched_tag = resolve_category(record)
    image_url, image_source = select_image_url(record, source_lang or record_lang)

    needs_ai = False
    if category_slug is None:
        needs_ai = True
    if source_lang and source_lang not in ("en", "fr"):
        needs_ai = True
    if not primary_brand:
        needs_ai = True

    provenance = {
        "name_source": name_source,
        "ingredients_source": ingredients_source,
        "source_lang": source_lang,
        "brand_source": brand_source,
        "category_source": matched_tag or "unmapped",
        "image_source": image_source,
    }

    return MappedProduct(
        barcode=barcode,
        name=name,
        name_i18n=name_i18n,
        brands=brands,
        primary_brand=primary_brand,
        category_slug=category_slug,
        unmapped_categories=unmapped_cats,
        raw_ingredients_text=ingredients_text,
        source_lang=source_lang,
        image_url=image_url,
        needs_ai=needs_ai,
        field_provenance=provenance,
    )
