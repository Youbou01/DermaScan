"""Structured prompt for translating raw label tokens into canonical INCI."""

import json

INCI_NORMALIZATION_SYSTEM_PROMPT = """You normalize cosmetic ingredient label tokens.
For each supplied token, return the same `original` value and a canonical uppercase INCI
name in `inci` only when you are confident. Do not invent ingredients. Set `inci` to null
when uncertain. Return only JSON matching the schema."""


def build_inci_normalization_prompt(tokens: list[str]) -> str:
    return f"Normalize these packaging-label ingredient tokens:\\n{json.dumps(tokens, ensure_ascii=False)}"
