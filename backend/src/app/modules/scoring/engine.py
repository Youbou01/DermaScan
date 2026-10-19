from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.core.enums import RiskLevel

__all__ = [
    "GOOD_MIN_COVERAGE",
    "GOOD_MIN_SCORE",
    "HIGH_RISK_SCORE_CAP",
    "MIN_COVERAGE_THRESHOLD",
    "MODERATE_MIN_SCORE",
    "SCORING_VERSION",
    "IngredientPositionInput",
    "RiskLevel",
    "ScoreBand",
    "ScoreOutput",
    "calculate_score",
]

# Bump whenever ANY number or rule below changes: the recompute job (scripts/recompute_scores.py)
# finds products with `scoring_version < SCORING_VERSION` and rescores them.
# The decisions behind these numbers are recorded in docs/adr/0004 (amendment of 2026-10-19).
SCORING_VERSION: int = 2


class ScoreBand(StrEnum):
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    INSUFFICIENT_DATA = "insufficient_data"


# Share of ingredients we must recognize before we publish a score at all.
MIN_COVERAGE_THRESHOLD: float = 0.70
# Share of ingredients we must recognize before a product may be called "good".
# Unknown ingredients are left out of the average, so without this a product that is half
# unknown could score 100: "unknown looks safe", which ADR-0004 forbids.
GOOD_MIN_COVERAGE: float = 0.80

HIGH_RISK_SCORE_CAP: int = 49
GOOD_MIN_SCORE: int = 75
MODERATE_MIN_SCORE: int = 40

BASE_POINTS: dict[RiskLevel, float] = {
    RiskLevel.LOW: 100.0,
    RiskLevel.MODERATE: 55.0,
    RiskLevel.HIGH: 10.0,
    RiskLevel.UNKNOWN: 0.0,
}


@dataclass(frozen=True)
class IngredientPositionInput:
    risk_level: RiskLevel
    position: int


@dataclass(frozen=True)
class ScoreOutput:
    score: int | None
    band: ScoreBand
    coverage: float
    scoring_version: int = SCORING_VERSION


def get_position_weight(position: int) -> float:
    clamped_pos = max(1, position)
    return 1.0 / (1.0 + 0.2 * (clamped_pos - 1))


def calculate_score(items: Sequence[IngredientPositionInput]) -> ScoreOutput:
    if not items:
        return ScoreOutput(score=None, band=ScoreBand.INSUFFICIENT_DATA, coverage=0.0)

    total = len(items)
    known = [i for i in items if i.risk_level != RiskLevel.UNKNOWN]
    coverage = round(len(known) / total, 4)

    if coverage < MIN_COVERAGE_THRESHOLD or not known:
        return ScoreOutput(score=None, band=ScoreBand.INSUFFICIENT_DATA, coverage=coverage)

    weighted_points = 0.0
    total_weight = 0.0
    has_high_risk = False

    for item in known:
        weight = get_position_weight(item.position)
        weighted_points += BASE_POINTS[item.risk_level] * weight
        total_weight += weight
        if item.risk_level == RiskLevel.HIGH:
            has_high_risk = True

    raw_score = round(weighted_points / total_weight)

    if has_high_risk:
        raw_score = min(raw_score, HIGH_RISK_SCORE_CAP)

    # Cap the score itself (not only the band) so the number and the band never disagree,
    # e.g. no "90, moderate" on screen.
    if coverage < GOOD_MIN_COVERAGE:
        raw_score = min(raw_score, GOOD_MIN_SCORE - 1)

    final_score = max(0, min(100, int(raw_score)))

    if final_score >= GOOD_MIN_SCORE and not has_high_risk:
        band = ScoreBand.GOOD
    elif final_score >= MODERATE_MIN_SCORE:
        band = ScoreBand.MODERATE
    else:
        band = ScoreBand.POOR

    return ScoreOutput(score=final_score, band=band, coverage=coverage)
