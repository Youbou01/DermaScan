import pytest

from app.modules.scoring.engine import (
    GOOD_MIN_COVERAGE,
    GOOD_MIN_SCORE,
    HIGH_RISK_SCORE_CAP,
    MIN_COVERAGE_THRESHOLD,
    IngredientPositionInput,
    RiskLevel,
    ScoreBand,
    calculate_score,
)


def _label(
    known: int, unknown: int, level: RiskLevel = RiskLevel.LOW
) -> list[IngredientPositionInput]:
    """A label with `known` rated ingredients followed by `unknown` unrecognized ones."""
    items = [IngredientPositionInput(level, position) for position in range(1, known + 1)]
    items += [
        IngredientPositionInput(RiskLevel.UNKNOWN, position)
        for position in range(known + 1, known + unknown + 1)
    ]
    return items


def test_empty_list_handled() -> None:
    result = calculate_score([])
    assert result.score is None
    assert result.band == ScoreBand.INSUFFICIENT_DATA
    assert result.coverage == 0.0


def test_unknown_ingredients_never_count_as_safe() -> None:
    # 3 of 4 recognized (coverage 0.75) and one of them is high concern.
    items = [
        IngredientPositionInput(RiskLevel.LOW, 1),
        IngredientPositionInput(RiskLevel.LOW, 2),
        IngredientPositionInput(RiskLevel.HIGH, 3),
        IngredientPositionInput(RiskLevel.UNKNOWN, 4),
    ]
    result = calculate_score(items)
    assert result.coverage == 0.75
    assert result.score is not None
    assert result.score <= HIGH_RISK_SCORE_CAP
    assert result.band != ScoreBand.GOOD


def test_mostly_unknown_label_is_insufficient_data_not_a_score() -> None:
    result = calculate_score(_label(known=1, unknown=2))
    assert result.band == ScoreBand.INSUFFICIENT_DATA
    assert result.score is None


def test_only_unknown_ingredients_is_insufficient_data() -> None:
    result = calculate_score(_label(known=0, unknown=4))
    assert result.band == ScoreBand.INSUFFICIENT_DATA
    assert result.score is None
    assert result.coverage == 0.0


def test_single_high_risk_ingredient_caps_band() -> None:
    items = [
        IngredientPositionInput(RiskLevel.LOW, 1),
        IngredientPositionInput(RiskLevel.LOW, 2),
        IngredientPositionInput(RiskLevel.LOW, 3),
        IngredientPositionInput(RiskLevel.LOW, 4),
        IngredientPositionInput(RiskLevel.HIGH, 5),
    ]
    result = calculate_score(items)
    assert result.score is not None
    assert result.score <= HIGH_RISK_SCORE_CAP
    assert result.band in {ScoreBand.MODERATE, ScoreBand.POOR}


def test_order_matters_for_position_weighting() -> None:
    early_moderate = [
        IngredientPositionInput(RiskLevel.MODERATE, 1),
        IngredientPositionInput(RiskLevel.LOW, 2),
        IngredientPositionInput(RiskLevel.LOW, 3),
    ]
    late_moderate = [
        IngredientPositionInput(RiskLevel.LOW, 1),
        IngredientPositionInput(RiskLevel.LOW, 2),
        IngredientPositionInput(RiskLevel.MODERATE, 3),
    ]
    res_early = calculate_score(early_moderate)
    res_late = calculate_score(late_moderate)

    assert res_early.score is not None
    assert res_late.score is not None
    assert res_early.score < res_late.score


# --- Coverage rules (ADR-0004 amendment, 2026-10-19) ------------------------------------------


def test_all_low_at_75_percent_coverage_is_capped_and_moderate() -> None:
    result = calculate_score(_label(known=3, unknown=1))  # coverage 0.75
    assert result.coverage == 0.75
    assert result.score is not None
    assert result.score <= GOOD_MIN_SCORE - 1
    assert result.band == ScoreBand.MODERATE


def test_coverage_below_minimum_is_insufficient_data() -> None:
    result = calculate_score(_label(known=13, unknown=7))  # coverage 0.65
    assert result.coverage == 0.65
    assert result.score is None
    assert result.band == ScoreBand.INSUFFICIENT_DATA


def test_all_low_at_90_percent_coverage_is_good() -> None:
    result = calculate_score(_label(known=9, unknown=1))  # coverage 0.90
    assert result.score == 100
    assert result.band == ScoreBand.GOOD


def test_minimum_coverage_boundary_is_inclusive() -> None:
    result = calculate_score(_label(known=7, unknown=3))  # coverage exactly 0.70
    assert result.coverage == MIN_COVERAGE_THRESHOLD
    assert result.score is not None
    assert result.band == ScoreBand.MODERATE


def test_good_coverage_boundary_is_inclusive() -> None:
    at_limit = calculate_score(_label(known=4, unknown=1))  # coverage exactly 0.80
    assert at_limit.coverage == GOOD_MIN_COVERAGE
    assert at_limit.score == 100
    assert at_limit.band == ScoreBand.GOOD

    just_below = calculate_score(_label(known=11, unknown=3))  # coverage 0.7857
    assert just_below.score == GOOD_MIN_SCORE - 1
    assert just_below.band == ScoreBand.MODERATE


def test_coverage_cap_never_raises_a_lower_score() -> None:
    result = calculate_score(_label(known=3, unknown=1, level=RiskLevel.MODERATE))
    assert result.score == 55  # the cap (74) only limits, it never lifts


@pytest.mark.parametrize("known", range(1, 13))
@pytest.mark.parametrize("unknown", range(0, 8))
def test_score_and_band_never_contradict_each_other(known: int, unknown: int) -> None:
    """No "90, moderate" on screen, and nothing good below the coverage bar."""
    result = calculate_score(_label(known=known, unknown=unknown))
    if result.score is None:
        assert result.band == ScoreBand.INSUFFICIENT_DATA
        return
    if result.score >= GOOD_MIN_SCORE:
        assert result.band == ScoreBand.GOOD
        assert result.coverage >= GOOD_MIN_COVERAGE
    else:
        assert result.band != ScoreBand.GOOD
