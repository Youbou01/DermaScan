"""scoring module: the pure, versioned scoring algorithm (no tables, no I/O).

Input: a list of ingredient ratings/risks and positions.
Output: score, band, confidence, is_estimated.
"""

from app.modules.scoring.engine import (
    DEFAULT_SCORING_PARAMS,
    INTERIM_RISK_TO_RATING,
    SCORING_VERSION,
    IngredientPositionInput,
    IngredientScoreInput,
    RiskLevel,
    ScoreOutput,
    ScoreResult,
    ScoringParams,
    calculate_score,
    get_position_weight,
)
from app.modules.scoring.service import get_current_scoring_version

__all__ = [
    "DEFAULT_SCORING_PARAMS",
    "INTERIM_RISK_TO_RATING",
    "SCORING_VERSION",
    "IngredientPositionInput",
    "IngredientScoreInput",
    "RiskLevel",
    "ScoreOutput",
    "ScoreResult",
    "ScoringParams",
    "calculate_score",
    "get_current_scoring_version",
    "get_position_weight",
]
