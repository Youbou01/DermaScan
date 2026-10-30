import json
from typing import Any

PRODUCT_ENRICHMENT_SYSTEM_PROMPT = (
    "You are an expert cosmetic formulation scientist and data normalizer.\n"
    "Your job is to extract structured skincare product data from packaging and web records.\n"
    "Rules:\n"
    "1. is_skincare: return true only for leave-on or rinse-off facial/body skincare.\n"
    "2. brand: extract canonical brand name or null if unknown. Never invent a brand.\n"
    "3. name_clean: clean, standardized product name without promotional claims.\n"
    "4. name_i18n: translations of name_clean for 'en' and 'fr'.\n"
    "5. category_slug: pick exactly one slug from the allowed categories list, or null.\n"
    "6. ingredients_inci: extract ingredients in label order with original and INCI.\n"
    "7. flags: add any relevant flags.\n"
    "8. Output ONLY valid JSON adhering strictly to the schema.\n"
)


def build_product_enrichment_prompt(
    mapped_product: dict[str, Any],
    valid_categories: list[dict[str, str]],
) -> str:
    category_list_str = "\n".join(f"- {c['slug']}: {c['name']}" for c in valid_categories)
    return (
        "Analyze and enrich the following product record:\n\n"
        f"Input Record:\n{json.dumps(mapped_product, ensure_ascii=False, indent=2)}\n\n"
        f"Allowed Category Slugs:\n{category_list_str}\n\n"
        "Respond with a JSON object matching the ProductEnrichmentResult schema.\n"
    )
