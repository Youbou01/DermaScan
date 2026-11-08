import json
from typing import Any

ALIAS_ADJUDICATION_SYSTEM_PROMPT = (
    "You are an expert cosmetic ingredient nomenclature specialist.\n"
    "Determine whether an unmatched raw ingredient label token is an alias or variant of\n"
    "one of the candidate canonical INCI names (from trigram similarity).\n"
    "Rules:\n"
    "- If the token refers to one candidate, return that candidate INCI name.\n"
    "- If ambiguous or unrelated, return matched_candidate: null.\n"
    "- Provide confidence between 0.0 and 1.0.\n"
    "- Output ONLY valid JSON adhering strictly to the schema.\n"
)


def build_alias_adjudication_prompt(items: list[dict[str, Any]]) -> str:
    return (
        "Adjudicate the following unmatched ingredient tokens against candidates:\n\n"
        f"Items:\n{json.dumps(items, ensure_ascii=False, indent=2)}\n\n"
        "Respond with a JSON object matching the AliasAdjudicationResult schema.\n"
    )
