"""ingredients module: the ingredient dictionary, aliases (synonyms), and the
parsing/normalization pipeline.

Owns tables: ingredient, ingredient_alias, ingredient_translation.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from here,
never from `models` or `repository` (enforced by import-linter).
"""

from app.modules.ingredients.admin import IngredientAdmin
from app.modules.ingredients.enums import AliasSource, RatingSource, ReviewStatus
from app.modules.ingredients.matching import Candidates, candidate_keys
from app.modules.ingredients.normalizer import normalize
from app.modules.ingredients.parser import (
    ParsedIngredient,
    Suspicion,
    looks_like_ingredient_list,
    parse_ingredient_label,
)
from app.modules.ingredients.schemas import (
    IngredientInfo,
    IngredientMatch,
    IngredientSuggestion,
    MatchType,
)
from app.modules.ingredients.service import IngredientService

__all__ = [
    "AliasSource",
    "Candidates",
    "IngredientAdmin",
    "IngredientInfo",
    "IngredientMatch",
    "IngredientService",
    "IngredientSuggestion",
    "MatchType",
    "ParsedIngredient",
    "RatingSource",
    "ReviewStatus",
    "Suspicion",
    "candidate_keys",
    "looks_like_ingredient_list",
    "normalize",
    "parse_ingredient_label",
]
