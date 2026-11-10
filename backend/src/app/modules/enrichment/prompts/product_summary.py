"""Prompt contract for concise, non-alarmist product summaries."""

import json

from app.modules.catalog import ProductDetail

PRODUCT_SUMMARY_SYSTEM_PROMPT = """You write plain-language skincare product summaries.
Return two short summaries, one in English (`en`) and one in French (`fr`).
Rules: grade-six reading level; maximum 40 words per language; two short sentences;
describe only supplied product facts; never use the words safe, unsafe, toxic, harmful,
or dangerous; do not make medical claims. Return only JSON matching the schema."""


def build_product_summary_prompt(product: ProductDetail) -> str:
    """Create a minimal factual input for the summary task; no hidden model context."""
    ingredients = [
        {
            "name": item.inci_name or item.name,
            "function": item.summary,
            "risk_level": item.risk_level.value,
        }
        for item in product.ingredients[:12]
    ]
    payload = {
        "name": product.name,
        "category": product.category.name if product.category else None,
        "ingredient_count": len(product.ingredients),
        "score_band": product.score_band.value,
        "ingredients": ingredients,
    }
    return (
        "Write the requested localized product summaries from these verified facts only:\\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
