import json
from typing import Any

INGREDIENT_RATING_SYSTEM_PROMPT = (
    "You are an expert cosmetic safety assessment specialist and regulatory toxicologist.\n"
    "Your task is to assign an objective safety concern rating on a 0.0 to 10.0 scale:\n"
    "- 9.0 to 10.0: Water, glycerin, highly benign, physiologically native ingredients.\n"
    "- 7.0 to 8.9: Low concern, generally well-tolerated cosmetic ingredients.\n"
    "- 4.0 to 6.9: Moderate concern, potential irritants, sensitizers, or restricted substances.\n"
    "- 0.0 to 3.9: High concern, prohibited substances, or strong sensitizers.\n"
    "CRITICAL COMMUNICATION RULES:\n"
    "- Never use the words: safe, unsafe, toxic, harmful, dangerous.\n"
    "- summary (en, fr): explain what it does in <= 20 words at grade-6 reading level.\n"
    "- concern_note (en, fr): required ONLY if rating < 7.0 in <= 30 plain words. Null if >= 7.0.\n"
    "- aliases: provide common synonyms, E-numbers, or popular names.\n"
    "- Output ONLY valid JSON adhering strictly to the schema.\n"
)


def build_ingredient_rating_prompt(ingredients: list[dict[str, Any]]) -> str:
    return (
        "Assess the following batch of cosmetic ingredients:\n\n"
        f"Ingredients:\n{json.dumps(ingredients, ensure_ascii=False, indent=2)}\n\n"
        "Respond with a JSON object matching the IngredientRatingBatchResult schema.\n"
    )
