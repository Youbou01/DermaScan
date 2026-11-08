"""Unit tests for deterministic Open Beauty Facts mapper."""

from app.modules.ingestion.mapper import (
    map_obf_record,
    resolve_category_slug,
)


def test_mapper_exact_category_matching_rejects_substring() -> None:
    # "en:hair-gels" should NOT match "en:gels"
    record = {
        "code": "3600522000001",
        "product_name": "Hair Gel Pro",
        "ingredients_text": "Aqua, Alcohol",
        "categories_tags": ["en:hair-gels", "en:styling-products"],
        "brands": "L'Oreal",
    }
    mapped = map_obf_record(record)
    assert mapped.category_slug is None
    assert "en:hair-gels" in mapped.unmapped_categories
    assert mapped.needs_ai is True


def test_mapper_resolves_exact_category_tags() -> None:
    record = {
        "code": "3600522000002",
        "product_name_fr": "Crème Hydratante Légère",
        "ingredients_text_fr": "Aqua, Glycerin, Dimethicone",
        "categories_tags": ["en:face-creams"],
        "brands": "CeraVe",
    }
    mapped = map_obf_record(record)
    assert mapped.category_slug == "moisturizer"
    assert mapped.source_lang == "fr"
    assert mapped.needs_ai is False


def test_mapper_unknown_category_does_not_default_to_moisturizer() -> None:
    record = {
        "code": "3600522000003",
        "product_name": "Mysterious Cosmetic",
        "ingredients_text": "Aqua, Parfum",
        "categories_tags": ["en:unknown-gadget"],
        "brands": "UnknownBrand",
    }
    mapped = map_obf_record(record)
    assert mapped.category_slug is None
    assert mapped.needs_ai is True


def test_mapper_extracts_brands_and_primary_brand() -> None:
    record = {
        "code": "3600522000004",
        "product_name": "Soothing Lotion",
        "ingredients_text": "Aqua, Glycerin",
        "brands": "La Roche-Posay, L'Oreal, La Roche-Posay",
        "categories_tags": ["en:body-lotions"],
    }
    mapped = map_obf_record(record)
    assert mapped.primary_brand == "La Roche-Posay"
    assert mapped.brands == ["La Roche-Posay", "L'Oreal"]
    assert mapped.category_slug == "body-lotion"


def test_mapper_rejects_ingredients_and_nutrition_images() -> None:
    record_with_ing_img = {
        "code": "3600522000005",
        "product_name": "Serum ABC",
        "ingredients_text": "Aqua, Niacinamide",
        "image_url": "https://images.openbeautyfacts.org/images/products/123/ingredients_fr.4.400.jpg",
        "categories_tags": ["en:serums"],
        "brands": "The Ordinary",
    }
    mapped_rejected = map_obf_record(record_with_ing_img)
    assert mapped_rejected.image_url is None

    record_with_front_img = {
        "code": "3600522000006",
        "product_name": "Serum XYZ",
        "ingredients_text": "Aqua, Niacinamide",
        "image_url": "https://images.openbeautyfacts.org/images/products/123/front_fr.4.400.jpg",
        "categories_tags": ["en:serums"],
        "brands": "The Ordinary",
    }
    mapped_accepted = map_obf_record(record_with_front_img)
    assert (
        mapped_accepted.image_url
        == "https://images.openbeautyfacts.org/images/products/123/front_fr.4.400.jpg"
    )


def test_mapper_language_preference_and_non_en_fr_sets_needs_ai() -> None:
    # Arabic / German label without EN/FR
    record = {
        "code": "3600522000007",
        "lang": "de",
        "product_name_de": "Tagescreme Sanft",
        "ingredients_text_de": "Aqua, Glyzerin",
        "categories_tags": ["en:face-creams"],
        "brands": "Nivea",
    }
    mapped = map_obf_record(record)
    assert mapped.name == "Tagescreme Sanft"
    assert mapped.source_lang == "de"
    assert mapped.category_slug == "moisturizer"
    assert mapped.needs_ai is True  # Because language is 'de', not 'en' or 'fr'


def test_resolve_category_slug_helper() -> None:
    assert resolve_category_slug(["en:sunscreens"]) == "sunscreen"
    assert resolve_category_slug(["en:face-masks"]) == "face-mask"
    assert resolve_category_slug(["en:unknown-xyz"]) is None
