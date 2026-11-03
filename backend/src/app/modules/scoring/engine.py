"""Pure deterministic product scoring engine (Scoring v4 — Zero Insufficient Data)."""

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
    "resolve_effective_rating_and_confidence",
]

SCORING_VERSION: int = 4

GOOD_MIN_SCORE: int = 75
MODERATE_MIN_SCORE: int = 50

INTERIM_RISK_TO_RATING: dict[RiskLevel, float | None] = {
    RiskLevel.LOW: 9.0,
    RiskLevel.MODERATE: 5.5,
    RiskLevel.HIGH: 2.0,
    RiskLevel.UNKNOWN: None,
}

_BENIGN_FUNCTIONS = frozenset(
    {
        "humectant",
        "emollient",
        "solvent",
        "skin conditioning",
        "skin protecting",
        "viscosity controlling",
        "bulking",
        "moisturising",
        "soothing",
        "antioxidant",
    }
)
_MODERATE_CONCERN_FUNCTIONS = frozenset(
    {
        "preservative",
        "uv absorber",
        "uv filter",
        "hair dyeing",
        "oxidizing",
        "reducing",
        "denaturant",
        "propellant",
        "depilatory",
    }
)


@dataclass(frozen=True, slots=True)
class ScoringParams:
    pessimistic_prior_d: float = 0.40
    position_weight_base: float = 0.85
    position_weight_floor: float = 0.05
    power_mean_q: float = 3.0
    prohibited_score_cap: int = 25
    insufficient_confidence_threshold: float = 0.0
    insufficient_ingredient_count: int = 1
    estimated_confidence_threshold: float = 0.60
    low_risk_min_score: int = GOOD_MIN_SCORE
    moderate_risk_min_score: int = MODERATE_MIN_SCORE


DEFAULT_SCORING_PARAMS = ScoringParams()


@dataclass(frozen=True, slots=True)
class IngredientScoreInput:
    position: int
    rating: float | None = None
    confidence: float = 1.0
    is_prohibited: bool = False
    is_restricted: bool = False
    is_allergen: bool = False
    functions: tuple[str, ...] = ()
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
        return self.confidence

    @property
    def scoring_version(self) -> int:
        return self.version

    @property
    def insufficient_data(self) -> bool:
        return self.score is None


ScoreOutput = ScoreResult


def resolve_effective_rating_and_confidence(
    item: IngredientScoreInput,
) -> tuple[float | None, float]:
    """Derive effective rating and confidence. Heuristic paths always use confidence <= 0.50
    so that heuristic-dependent scores are consistently flagged with is_estimated=True.
    """
    if item.is_prohibited:
        return 0.5, 0.55 if item.rating is None else max(0.55, float(item.confidence))
    if item.rating is not None:
        return float(item.rating), max(0.0, min(1.0, float(item.confidence)))
    if item.is_restricted:
        return 4.5, 0.45
    if item.is_allergen:
        return 5.0, 0.45
    if item.functions:
        norm_fns = {f.strip().lower() for f in item.functions if f}
        if norm_fns & _MODERATE_CONCERN_FUNCTIONS:
            return 5.5, 0.40
        if norm_fns & _BENIGN_FUNCTIONS:
            return 8.0, 0.50
        return 7.0, 0.35
    return None, 0.0


def get_position_weight(position: int, params: ScoringParams = DEFAULT_SCORING_PARAMS) -> float:
    p = max(1, position)
    return max(params.position_weight_floor, params.position_weight_base ** (p - 1))


def calculate_score(
    items: Sequence[IngredientScoreInput | IngredientPositionInput],
    params: ScoringParams = DEFAULT_SCORING_PARAMS,
) -> ScoreResult:
    if not items:
        return ScoreResult(
            score=params.moderate_risk_min_score,
            band=RiskLevel.MODERATE,
            confidence=0.10,
            is_estimated=True,
            version=SCORING_VERSION,
        )

    score_inputs: list[IngredientScoreInput] = [
        item.to_score_input() if isinstance(item, IngredientPositionInput) else item
        for item in items
    ]

    use_percentages = all(
        it.estimated_percent is not None and it.estimated_percent > 0 for it in score_inputs
    )
    percent_sum = (
        sum(it.estimated_percent or 0.0 for it in score_inputs) if use_percentages else 0.0
    )

    weights: list[float] = []
    d_stars: list[float] = []
    confs: list[float] = []
    any_prohibited = False

    for it in score_inputs:
        if it.is_prohibited:
            any_prohibited = True
        eff_rating, eff_conf = resolve_effective_rating_and_confidence(it)
        if use_percentages and percent_sum > 0:
            w = (it.estimated_percent or 0.0) / percent_sum
        else:
            w = get_position_weight(it.position, params)
        d = (1.0 - (eff_rating / 10.0)) if eff_rating is not None else params.pessimistic_prior_d
        d_star = eff_conf * d + (1.0 - eff_conf) * params.pessimistic_prior_d

        weights.append(w)
        d_stars.append(max(0.0, min(1.0, d_star)))
        confs.append(eff_conf)

    weight_sum = sum(weights)
    if weight_sum <= 0:
        weight_sum = 1.0

    k_conf = round(sum(w * c for w, c in zip(weights, confs, strict=True)) / weight_sum, 3)
    q = params.power_mean_q
    c_agg = (sum(w * (ds**q) for w, ds in zip(weights, d_stars, strict=True)) / weight_sum) ** (
        1.0 / q
    )

    raw_score = round(100.0 * (1.0 - c_agg))
    score = max(0, min(100, raw_score))
    if any_prohibited:
        score = min(score, params.prohibited_score_cap)

    is_estimated = k_conf < params.estimated_confidence_threshold or len(score_inputs) < 3

    if any_prohibited or score < params.moderate_risk_min_score:
        band = RiskLevel.HIGH
    elif score < params.low_risk_min_score:
        band = RiskLevel.MODERATE
    else:
        band = RiskLevel.LOW

    return ScoreResult(
        score=score,
        band=band,
        confidence=k_conf,
        is_estimated=is_estimated,
        version=SCORING_VERSION,
    )
