from app.modules.scoring.engine import (
    HIGH_RISK_SCORE_CAP,
    IngredientPositionInput,
    RiskLevel,
    ScoreBand,
    calculate_score,
)


def test_empty_list_handled() -> None:
    result = calculate_score([])
    assert result.score is None
    assert result.band == ScoreBand.INSUFFICIENT_DATA
    assert result.coverage == 0.0


def test_unknown_ingredients_never_count_as_safe() -> None:
    items = [
        IngredientPositionInput(RiskLevel.LOW, 1),
        IngredientPositionInput(RiskLevel.HIGH, 2),
        IngredientPositionInput(RiskLevel.UNKNOWN, 3),
        IngredientPositionInput(RiskLevel.UNKNOWN, 4),
    ]
    result = calculate_score(items)
    assert result.coverage == 0.5
    assert result.score is not None
    assert result.score <= HIGH_RISK_SCORE_CAP
    assert result.band != ScoreBand.GOOD

    low_cov_items = [
        IngredientPositionInput(RiskLevel.LOW, 1),
        IngredientPositionInput(RiskLevel.UNKNOWN, 2),
        IngredientPositionInput(RiskLevel.UNKNOWN, 3),
    ]
    low_cov_result = calculate_score(low_cov_items)
    assert low_cov_result.band == ScoreBand.INSUFFICIENT_DATA
    assert low_cov_result.score is None


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
