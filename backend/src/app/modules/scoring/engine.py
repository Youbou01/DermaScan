from collections.abc import Sequence
from dataclasses import dataclass

from app.core.enums import RiskLevel

__all__ = [
    "DEFAULT_SCORING_PARAMS",
    "GOOD_MIN_SCORE",
    "INTERIM_RISK_TO_RATING",
    "MODERATE_MIN_SCORE",
    "SCORING_VERSION",
    "IngredientPositionInput",
    "IngredientScoreInput",
    "RiskLevel",
    "ScoreOutput",
    "ScoreResult",
    "ScoringParams",
    "calculate_score",
    "get_position_weight",
]

# Bump whenever ANY mathematical formula or constant changes.
# The decisions behind these numbers are recorded in docs/adr/0015-scoring-v3.md.
SCORING_VERSION: int = 3


@dataclass(frozen=True, slots=True)
class ScoringParams:
    pessimistic_prior_d: float = 0.4
    position_weight_base: float = 0.85
    position_weight_floor: float = 0.05
    power_mean_q: float = 3.0
    prohibited_score_cap: int = 25
    insufficient_confidence_threshold: float = 0.35
    insufficient_ingredient_count: int = 3
    estimated_confidence_threshold: float = 0.60
    low_risk_min_score: int = 75
    moderate_risk_min_score: int = 50


DEFAULT_SCORING_PARAMS = ScoringParams()

# Backward-compatibility constants
GOOD_MIN_SCORE: int = DEFAULT_SCORING_PARAMS.low_risk_min_score
MODERATE_MIN_SCORE: int = DEFAULT_SCORING_PARAMS.moderate_risk_min_score

INTERIM_RISK_TO_RATING: dict[RiskLevel, float | None] = {
    RiskLevel.LOW: 9.0,
    RiskLevel.MODERATE: 5.5,
    RiskLevel.HIGH: 2.0,
    RiskLevel.UNKNOWN: None,
}


@dataclass(frozen=True, slots=True)
class IngredientScoreInput:
    position: int
    rating: float | None
    confidence: float = 1.0
    is_prohibited: bool = False
    estimated_percent: float | None = None


@dataclass(frozen=True, slots=True)
class IngredientPositionInput:
    risk_level: RiskLevel
    position: int
    is_prohibited: bool = False
    estimated_percent: float | None = None

    def to_score_input(self) -> IngredientScoreInput:
        rating = INTERIM_RISK_TO_RATING.get(self.risk_level)
        conf = 0.0 if self.risk_level == RiskLevel.UNKNOWN or rating is None else 1.0
        return IngredientScoreInput(
            position=self.position,
            rating=rating,
            confidence=conf,
            is_prohibited=self.is_prohibited,
            estimated_percent=self.estimated_percent,
        )


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: int | None
    band: RiskLevel
    confidence: float
    is_estimated: bool
    version: int = SCORING_VERSION

    @property
    def coverage(self) -> float:
        """Backward-compatible alias for exposure-weighted confidence K."""
        return self.confidence

    @property
    def scoring_version(self) -> int:
        return self.version

    @property
    def insufficient_data(self) -> bool:
        return self.score is None


# Backward-compatible alias
ScoreOutput = ScoreResult


def get_position_weight(position: int, params: ScoringParams = DEFAULT_SCORING_PARAMS) -> float:
    clamped_pos = max(1, position)
    return max(params.position_weight_floor, params.position_weight_base ** (clamped_pos - 1))


def calculate_score(
    items: Sequence[IngredientScoreInput | IngredientPositionInput],
    params: ScoringParams = DEFAULT_SCORING_PARAMS,
) -> ScoreResult:
    """Pure Scoring v3 mathematical formula."""
    if not items:
        return ScoreResult(
            score=None,
            band=RiskLevel.UNKNOWN,
            confidence=0.0,
            is_estimated=True,
            version=SCORING_VERSION,
        )

    score_inputs: list[IngredientScoreInput] = [
        item.to_score_input() if isinstance(item, IngredientPositionInput) else item
        for item in items
    ]

    has_all_percents = all(
        i.estimated_percent is not None and i.estimated_percent >= 0 for i in score_inputs
    )
    percent_sum = sum(i.estimated_percent or 0.0 for i in score_inputs) if has_all_percents else 0.0

    weights: list[float] = []
    d_stars: list[float] = []
    confs: list[float] = []
    any_prohibited = False

    for item in score_inputs:
        if item.is_prohibited:
            any_prohibited = True

        if has_all_percents and percent_sum > 0:
            w = (item.estimated_percent or 0.0) / percent_sum
        else:
            p = max(1, item.position)
            w = max(params.position_weight_floor, params.position_weight_base ** (p - 1))

        if item.rating is None:
            d = 0.0
            c = 0.0
        else:
            d = 1.0 - (item.rating / 10.0)
            c = max(0.0, min(1.0, item.confidence))

        d_star = c * d + (1.0 - c) * params.pessimistic_prior_d
        weights.append(w)
        d_stars.append(d_star)
        confs.append(c)

    sum_w = sum(weights)
    if sum_w <= 0.0:
        return ScoreResult(
            score=None,
            band=RiskLevel.UNKNOWN,
            confidence=0.0,
            is_estimated=True,
            version=SCORING_VERSION,
        )

    raw_k = sum(w * c for w, c in zip(weights, confs, strict=False)) / sum_w
    k = round(raw_k, 3)

    is_estimated = k < params.estimated_confidence_threshold
    is_insufficient = (
        k < params.insufficient_confidence_threshold
        or len(score_inputs) < params.insufficient_ingredient_count
    )

    if is_insufficient:
        return ScoreResult(
            score=None,
            band=RiskLevel.UNKNOWN,
            confidence=k,
            is_estimated=is_estimated,
            version=SCORING_VERSION,
        )

    weighted_d_cubed = sum(
        w * (d_star**params.power_mean_q) for w, d_star in zip(weights, d_stars, strict=False)
    )
    c_agg = (weighted_d_cubed / sum_w) ** (1.0 / params.power_mean_q)

    score = round(100.0 * (1.0 - c_agg))
    score = max(0, min(100, score))

    if any_prohibited:
        score = min(score, params.prohibited_score_cap)
        band = RiskLevel.HIGH
    elif score >= params.low_risk_min_score:
        band = RiskLevel.LOW
    elif score >= params.moderate_risk_min_score:
        band = RiskLevel.MODERATE
    else:
        band = RiskLevel.HIGH

    return ScoreResult(
        score=score,
        band=band,
        confidence=k,
        is_estimated=is_estimated,
        version=SCORING_VERSION,
    )
