"""ingredients module: the ingredient dictionary, aliases (synonyms), and the
parsing/normalization pipeline.

Owns tables: ingredient, ingredient_alias, ingredient_translation.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from here,
never from `models` or `repository` (enforced by import-linter).
"""

from app.modules.ingredients.matching import Candidates, candidate_keys
from app.modules.ingredients.normalizer import normalize
from app.modules.ingredients.parser import ParsedIngredient, parse_ingredient_label
from app.modules.ingredients.schemas import (
    IngredientInfo,
    IngredientMatch,
    IngredientSuggestion,
    MatchType,
)
from app.modules.ingredients.service import IngredientService

__all__ = [
    "Candidates",
    "IngredientInfo",
    "IngredientMatch",
    "IngredientService",
    "IngredientSuggestion",
    "MatchType",
    "ParsedIngredient",
    "candidate_keys",
    "normalize",
    "parse_ingredient_label",
]
