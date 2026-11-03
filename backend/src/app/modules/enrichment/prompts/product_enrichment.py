import json
from typing import Any

PRODUCT_ENRICHMENT_SYSTEM_PROMPT = (
    "You are an expert cosmetic formulation scientist and data normalizer.\n"
    "Your job is to extract structured skincare product data from packaging, web records, "
    "and search context.\n"
    "Rules:\n"
    "1. is_skincare: return true only for leave-on or rinse-off facial/body skincare.\n"
    "2. brand: extract or infer canonical brand name from title/context "
    "(never leave null when brand is identifiable).\n"
    "3. name_clean: clean, standardized product name without promotional claims.\n"
    "4. name_i18n: translations of name_clean for 'en' and 'fr'.\n"
    "5. category_slug: when is_skincare is true, pick the closest matching slug "
    "from the allowed categories list.\n"
    "6. ingredients_inci: extract ingredients in label order with original and "
    "standard uppercase INCI name. "
    "If raw ingredients text is missing or marketing-only, reconstruct ingredients_inci "
    "from web_snippets context.\n"
    "7. flags: add any relevant flags.\n"
    "8. Output ONLY valid JSON adhering strictly to the schema.\n"
)


def build_product_enrichment_prompt(
    mapped_product: dict[str, Any],
    valid_categories: list[dict[str, str]],
) -> str:
    category_list_str = "\n".join(f"- {c['slug']}: {c['name']}" for c in valid_categories)
    web_context_str = ""
    if mapped_product.get("web_snippets"):
        web_context_str = f"\nWeb Search Context:\n{mapped_product['web_snippets']}\n\n"
    return (
        "Analyze and enrich the following product record:\n\n"
        f"Input Record:\n{json.dumps(mapped_product, ensure_ascii=False, indent=2)}\n\n"
        f"{web_context_str}"
        f"Allowed Category Slugs:\n{category_list_str}\n\n"
        "Respond with a JSON object matching the ProductEnrichmentResult schema.\n"
    )
