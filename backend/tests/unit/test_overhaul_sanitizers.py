"""Regression tests for backend fixes and in-place retro-sanitizers."""

import uuid

import pytest

from app.core.enums import RiskLevel
from app.modules.catalog.service import _ingredient_out
from app.modules.ingestion.mapper import _clean_brand_token
from app.modules.ingredients import IngredientInfo, is_valid_ingredient_token


@pytest.mark.parametrize(
    "token",
    [
        "1!!",
        "1",
        "20",
        "N",
        "a",
        "(F01)",
        "G2047548",
        "C142090",
        "0.1g",
        "&lt",
        "",
    ],
)
def test_is_valid_ingredient_token_rejects_garbage(token: str) -> None:
    assert not is_valid_ingredient_token(token)


@pytest.mark.parametrize(
    "token",
    [
        "AQUA",
        "GLYCERIN",
        "1,2-HEXANEDIOL",
        "CI 77891",
        "TOCOPHEROL",
        "PEG-40 HYDROGENATED CASTOR OIL",
    ],
)
def test_is_valid_ingredient_token_accepts_valid_ingredients(token: str) -> None:
    assert is_valid_ingredient_token(token)


def test_clean_brand_token_normalizes_obf_tags_and_preserves_valid_prefixes() -> None:
    assert _clean_brand_token("xx:unil", from_tags=True) == "Unil"
    assert _clean_brand_token("xx:johnson-s-baby", from_tags=True) == "Johnson S Baby"
    assert _clean_brand_token("BIO:VEGANE", from_tags=False) == "BIO:VEGANE"


def test_ingredient_out_heuristic_consistency() -> None:
    # 1. CosIng function heuristic derives rating=8.0, confidence=0.5, risk=LOW
    info_with_fns = IngredientInfo(
        id=uuid.uuid4(),
        inci_name="TEST EMOLLIENT",
        risk_level=RiskLevel.UNKNOWN,
        rating=None,
        rating_confidence=None,
        summary=None,
        is_prohibited=False,
        is_restricted=False,
        is_allergen=False,
        functions=("emollient", "skin conditioning"),
    )
    out_with_fns = _ingredient_out(position=1, raw_text="TEST EMOLLIENT", info=info_with_fns)
    assert out_with_fns.rating == 8.0
    assert out_with_fns.confidence == 0.5
    assert out_with_fns.risk_level == RiskLevel.LOW

    # 2. Unknown ingredient without functions remains unrated
    info_unknown = IngredientInfo(
        id=uuid.uuid4(),
        inci_name="TEST UNKNOWN",
        risk_level=RiskLevel.UNKNOWN,
        rating=None,
        rating_confidence=None,
        summary=None,
        is_prohibited=False,
        is_restricted=False,
        is_allergen=False,
        functions=(),
    )
    out_unknown = _ingredient_out(position=1, raw_text="TEST UNKNOWN", info=info_unknown)
    assert out_unknown.rating is None
    assert out_unknown.confidence is None
    assert out_unknown.risk_level == RiskLevel.UNKNOWN
