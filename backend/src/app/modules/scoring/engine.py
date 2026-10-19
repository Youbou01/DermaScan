from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

SCORING_VERSION: int = 1


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class ScoreBand(StrEnum):
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    INSUFFICIENT_DATA = "insufficient_data"


MIN_COVERAGE_THRESHOLD: float = 0.50
HIGH_RISK_SCORE_CAP: int = 49

BASE_POINTS: dict[RiskLevel, float] = {
    RiskLevel.LOW: 100.0,
    RiskLevel.MODERATE: 55.0,
    RiskLevel.HIGH: 10.0,
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

    final_score = max(0, min(100, int(raw_score)))

    if final_score >= 75 and not has_high_risk:
        band = ScoreBand.GOOD
    elif final_score >= 40:
        band = ScoreBand.MODERATE
    else:
        band = ScoreBand.POOR

    return ScoreOutput(score=final_score, band=band, coverage=coverage)
