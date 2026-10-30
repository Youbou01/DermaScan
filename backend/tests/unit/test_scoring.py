import pytest

from app.core.enums import RiskLevel
from app.modules.scoring import (
    DEFAULT_SCORING_PARAMS,
    IngredientPositionInput,
    IngredientScoreInput,
    calculate_score,
)


def _benign(pos: int, conf: float = 1.0) -> IngredientScoreInput:
    return IngredientScoreInput(position=pos, rating=9.5, confidence=conf)


def _moderate(pos: int, conf: float = 1.0) -> IngredientScoreInput:
    return IngredientScoreInput(position=pos, rating=5.0, confidence=conf)


def _high(pos: int, conf: float = 1.0) -> IngredientScoreInput:
    return IngredientScoreInput(position=pos, rating=2.0, confidence=conf)


def _unknown(pos: int) -> IngredientScoreInput:
    return IngredientScoreInput(position=pos, rating=None, confidence=0.0)


# --- 10 Exact Test Vectors from Specification Section 5.2 ---


def test_vector_1_twenty_benign() -> None:
    # 20 benign => score = 95, K = 1.000, insufficient = False, estimated = False
    items = [_benign(i) for i in range(1, 21)]
    result = calculate_score(items)
    assert result.score == 95
    assert result.band == RiskLevel.LOW
    assert result.confidence == 1.000
    assert not result.insufficient_data
    assert not result.is_estimated


def test_vector_2_nineteen_benign_one_high_at_pos_8() -> None:
    # 19 benign + 1 high at pos 8 => score = 70, K = 1.000, insufficient = False, estimated = False
    items = [_high(8) if i == 8 else _benign(i) for i in range(1, 21)]
    result = calculate_score(items)
    assert result.score == 70
    assert result.band == RiskLevel.MODERATE
    assert result.confidence == 1.000
    assert not result.insufficient_data
    assert not result.is_estimated


def test_vector_3_one_high_at_pos_1_nineteen_benign() -> None:
    # 1 high at pos 1 + 19 benign => score = 57, K = 1.000, insufficient = False, estimated = False
    items = [_high(1)] + [_benign(i) for i in range(2, 21)]
    result = calculate_score(items)
    assert result.score == 57
    assert result.band == RiskLevel.MODERATE
    assert result.confidence == 1.000
    assert not result.insufficient_data
    assert not result.is_estimated


def test_vector_4_nineteen_benign_one_high_at_pos_20() -> None:
    # 19 benign + 1 high at pos 20 => score = 84, K = 1.000, insufficient = False, estimated = False
    items = [_benign(i) for i in range(1, 20)] + [_high(20)]
    result = calculate_score(items)
    assert result.score == 84
    assert result.band == RiskLevel.LOW
    assert result.confidence == 1.000
    assert not result.insufficient_data
    assert not result.is_estimated


def test_vector_5_ten_unknown() -> None:
    # 10 unknown => score = None, K = 0.000, insufficient = True, estimated = True
    items = [_unknown(i) for i in range(1, 11)]
    result = calculate_score(items)
    assert result.score is None
    assert result.band == RiskLevel.UNKNOWN
    assert result.confidence == 0.000
    assert result.insufficient_data
    assert result.is_estimated


def test_vector_6_six_benign_four_unknown_last() -> None:
    # 6 benign + 4 unknown (last) => score = 76, K = 0.776, insufficient = False, estimated = False
    items = [_benign(i) for i in range(1, 7)] + [_unknown(i) for i in range(7, 11)]
    result = calculate_score(items)
    assert result.score == 76
    assert result.band == RiskLevel.LOW
    assert result.confidence == 0.776
    assert not result.insufficient_data
    assert not result.is_estimated


def test_vector_7_one_unknown_at_pos_1_nine_benign() -> None:
    # 1 unknown at pos 1 + 9 benign => score = 77, K = 0.813, insuff = False, est = False
    items = [_unknown(1)] + [_benign(i) for i in range(2, 11)]
    result = calculate_score(items)
    assert result.score == 77
    assert result.band == RiskLevel.LOW
    assert result.confidence == 0.813
    assert not result.insufficient_data
    assert not result.is_estimated


def test_vector_8_five_moderate_fifteen_benign() -> None:
    # 5 moderate + 15 benign => score = 58, K = 1.000, insufficient = False, estimated = False
    items = [_moderate(i) for i in range(1, 6)] + [_benign(i) for i in range(6, 21)]
    result = calculate_score(items)
    assert result.score == 58
    assert result.band == RiskLevel.MODERATE
    assert result.confidence == 1.000
    assert not result.insufficient_data
    assert not result.is_estimated


def test_vector_9_two_benign_only() -> None:
    # 2 benign only (n < 3) => score = None, K = 1.000, insufficient = True, estimated = False
    items = [_benign(1), _benign(2)]
    result = calculate_score(items)
    assert result.score is None
    assert result.band == RiskLevel.UNKNOWN
    assert result.confidence == 1.000
    assert result.insufficient_data
    assert not result.is_estimated


def test_vector_10_ten_benign_with_confidence_half() -> None:
    # 10 benign with c = 0.5 => score = 77, K = 0.500, insufficient = False, estimated = True
    items = [_benign(i, conf=0.5) for i in range(1, 11)]
    result = calculate_score(items)
    assert result.score == 77
    assert result.band == RiskLevel.LOW
    assert result.confidence == 0.500
    assert not result.insufficient_data
    assert result.is_estimated


# --- Additional Boundary & Rule Tests ---


def test_empty_list() -> None:
    result = calculate_score([])
    assert result.score is None
    assert result.band == RiskLevel.UNKNOWN
    assert result.confidence == 0.0
    assert result.insufficient_data
    assert result.is_estimated


def test_prohibited_ingredient_forces_cap_and_high_risk() -> None:
    # Even if 19 items are benign, a prohibited item caps score at 25 and band = high
    items = [_benign(i) for i in range(1, 20)] + [
        IngredientScoreInput(position=20, rating=0.5, confidence=1.0, is_prohibited=True)
    ]
    result = calculate_score(items)
    assert result.score is not None
    assert result.score <= DEFAULT_SCORING_PARAMS.prohibited_score_cap
    assert result.band == RiskLevel.HIGH


def test_interim_ingredient_position_input_compatibility() -> None:
    # Verify backward-compatible conversion from RiskLevel
    items: list[IngredientPositionInput] = [
        IngredientPositionInput(risk_level=RiskLevel.LOW, position=1),
        IngredientPositionInput(risk_level=RiskLevel.LOW, position=2),
        IngredientPositionInput(risk_level=RiskLevel.LOW, position=3),
    ]
    result = calculate_score(items)
    assert result.score is not None
    assert result.score >= 75
    assert result.band == RiskLevel.LOW
    assert result.confidence == 1.0


# --- Property Tests ---


@pytest.mark.parametrize("target_pos", [1, 5, 10])
def test_property_lowering_ingredient_rating_never_increases_score(target_pos: int) -> None:
    base_items = [_benign(i) for i in range(1, 11)]
    score_base = calculate_score(base_items).score
    assert score_base is not None

    for degraded_rating in [8.0, 5.0, 2.0, 0.0]:
        degraded_items = [
            IngredientScoreInput(position=i, rating=degraded_rating, confidence=1.0)
            if i == target_pos
            else _benign(i)
            for i in range(1, 11)
        ]
        score_degraded = calculate_score(degraded_items).score
        assert score_degraded is not None
        assert score_degraded <= score_base


@pytest.mark.parametrize("rating", [0.0, 1.5, 5.0, 7.5, 10.0])
@pytest.mark.parametrize("conf", [0.0, 0.35, 0.5, 0.8, 1.0])
def test_property_score_always_bounded_between_0_and_100(rating: float, conf: float) -> None:
    items = [IngredientScoreInput(position=i, rating=rating, confidence=conf) for i in range(1, 8)]
    res = calculate_score(items)
    if res.score is not None:
        assert 0 <= res.score <= 100


def test_property_adding_unknown_never_raises_confidence() -> None:
    base = [_benign(i) for i in range(1, 6)]
    k_base = calculate_score(base).confidence

    extended = base + [_unknown(i) for i in range(6, 11)]
    k_extended = calculate_score(extended).confidence

    assert k_extended <= k_base
