"""Unit tests for the pure suitability engine (no database)."""

import uuid

import pytest

from app.modules.identity.enums import AlertCode, AlertSeverity, SkinType, Verdict
from app.modules.identity.schemas import HealthCondition, SuitabilityOut
from app.modules.identity.suitability import (
    DRYING_NAMES,
    HEAVY_OCCLUSIVE_NAMES,
    PREGNANCY_UNSAFE_NAMES,
    IngredientFacts,
    ProfileFacts,
    evaluate_suitability,
)

PRODUCT_ID = uuid.uuid4()

PREGNANCY_TITLE = {
    "en": "Not recommended during pregnancy",
    "fr": "Déconseillé pendant la grossesse",
}
ALLERGY_TITLE = {
    "en": "Matches your allergy or sensitivity profile",
    "fr": "Correspond à votre profil d'allergie ou de sensibilité",
}
BLACKLIST_TITLE = {"en": "On your blacklist", "fr": "Dans votre liste noire"}
SKIN_TITLE = {
    "en": "May not suit your skin type",
    "fr": "Peut ne pas convenir à votre type de peau",
}

PREGNANT = ProfileFacts(is_pregnant_or_nursing=True)


def _ing(name: str, **kwargs: bool) -> IngredientFacts:
    return IngredientFacts(ingredient_id=uuid.uuid4(), name=name, **kwargs)


def _run(
    profile: ProfileFacts, ingredients: list[IngredientFacts], locale: str = "en"
) -> SuitabilityOut:
    return evaluate_suitability(PRODUCT_ID, profile, ingredients, locale)


def test_empty_ingredients_is_suitable() -> None:
    result = _run(PREGNANT, [])
    assert result.product_id == PRODUCT_ID
    assert result.verdict == Verdict.SUITABLE
    assert result.suits_profile is True
    assert result.has_risk_alert is False
    assert result.is_blacklisted is False
    assert result.alerts == []


def test_harmless_ingredient_is_suitable() -> None:
    result = _run(PREGNANT, [_ing("GLYCERIN")])
    assert result.verdict == Verdict.SUITABLE
    assert result.alerts == []


@pytest.mark.parametrize("locale", ["en", "fr"])
@pytest.mark.parametrize("name", sorted(PREGNANCY_UNSAFE_NAMES))
def test_pregnancy_names_give_high_alert(name: str, locale: str) -> None:
    result = _run(PREGNANT, [_ing(name)], locale)
    [alert] = result.alerts
    assert alert.code == AlertCode.PREGNANCY_CONTRAINDICATION
    assert alert.severity == AlertSeverity.HIGH
    assert alert.ingredient_name == name
    assert alert.title == PREGNANCY_TITLE[locale]
    assert name in alert.detail
    assert result.verdict == Verdict.AVOID
    assert result.suits_profile is False
    assert result.has_risk_alert is True


def test_pregnancy_french_detail() -> None:
    [alert] = _run(PREGNANT, [_ing("RETINOL")], "fr").alerts
    assert alert.detail == "Contient RETINOL, contre-indiqué pendant la grossesse et l'allaitement."


def test_pregnancy_rules_ignored_when_not_pregnant() -> None:
    result = _run(ProfileFacts(), [_ing("RETINOL"), _ing("X", is_prohibited=True)])
    assert result.alerts == []
    assert result.verdict == Verdict.SUITABLE


@pytest.mark.parametrize("locale", ["en", "fr"])
def test_prohibited_flag_with_pregnancy(locale: str) -> None:
    result = _run(PREGNANT, [_ing("SOME PROHIBITED THING", is_prohibited=True)], locale)
    [alert] = result.alerts
    assert alert.code == AlertCode.PREGNANCY_CONTRAINDICATION
    assert alert.title == PREGNANCY_TITLE[locale]
    assert result.verdict == Verdict.AVOID


@pytest.mark.parametrize("locale", ["en", "fr"])
def test_declared_allergy_gives_high_alert(locale: str) -> None:
    item = _ing("LINALOOL")
    profile = ProfileFacts(allergy_ingredient_ids=frozenset({item.ingredient_id}))
    result = _run(profile, [item, _ing("GLYCERIN")], locale)
    [alert] = result.alerts
    assert alert.code == AlertCode.ALLERGY_MATCH
    assert alert.severity == AlertSeverity.HIGH
    assert alert.ingredient_name == "LINALOOL"
    assert alert.title == ALLERGY_TITLE[locale]
    assert result.verdict == Verdict.AVOID


@pytest.mark.parametrize(
    "profile",
    [
        ProfileFacts(skin_type=SkinType.SENSITIVE),
        ProfileFacts(health_conditions=frozenset({HealthCondition.ECZEMA})),
        ProfileFacts(health_conditions=frozenset({HealthCondition.ROSACEA})),
    ],
)
@pytest.mark.parametrize("locale", ["en", "fr"])
def test_allergen_flag_with_sensitive_profile(profile: ProfileFacts, locale: str) -> None:
    [alert] = _run(profile, [_ing("LIMONENE", is_allergen=True)], locale).alerts
    assert alert.code == AlertCode.ALLERGY_MATCH
    assert alert.title == ALLERGY_TITLE[locale]


@pytest.mark.parametrize(
    "profile",
    [
        ProfileFacts(skin_type=SkinType.NORMAL),
        ProfileFacts(health_conditions=frozenset({HealthCondition.PSORIASIS})),
        ProfileFacts(),
    ],
)
def test_allergen_flag_ignored_without_sensitive_profile(profile: ProfileFacts) -> None:
    assert _run(profile, [_ing("LIMONENE", is_allergen=True)]).alerts == []


@pytest.mark.parametrize("locale", ["en", "fr"])
def test_blacklisted_ingredient_gives_high_alert(locale: str) -> None:
    item = _ing("PARFUM")
    profile = ProfileFacts(blacklisted_ingredient_ids=frozenset({item.ingredient_id}))
    result = _run(profile, [item], locale)
    [alert] = result.alerts
    assert alert.code == AlertCode.BLACKLISTED
    assert alert.severity == AlertSeverity.HIGH
    assert alert.ingredient_name == "PARFUM"
    assert alert.title == BLACKLIST_TITLE[locale]
    assert result.is_blacklisted is True
    assert result.has_risk_alert is True
    assert result.verdict == Verdict.AVOID


def test_blacklisted_product_has_no_alert() -> None:
    result = _run(ProfileFacts(product_is_blacklisted=True), [_ing("GLYCERIN")])
    assert result.alerts == []
    assert result.is_blacklisted is True
    assert result.has_risk_alert is True
    assert result.verdict == Verdict.AVOID
    assert result.suits_profile is False


@pytest.mark.parametrize("skin_type", [SkinType.DRY, SkinType.SENSITIVE])
@pytest.mark.parametrize("locale", ["en", "fr"])
@pytest.mark.parametrize("name", sorted(DRYING_NAMES))
def test_drying_names_for_dry_or_sensitive(name: str, skin_type: SkinType, locale: str) -> None:
    result = _run(ProfileFacts(skin_type=skin_type), [_ing(name)], locale)
    [alert] = result.alerts
    assert alert.code == AlertCode.SKIN_TYPE_MISMATCH
    assert alert.severity == AlertSeverity.MEDIUM
    assert alert.title == SKIN_TITLE[locale]
    assert result.verdict == Verdict.CAUTION
    assert result.suits_profile is False
    assert result.has_risk_alert is True
    assert result.is_blacklisted is False


@pytest.mark.parametrize("skin_type", [SkinType.OILY, SkinType.NORMAL, SkinType.COMBINATION])
def test_drying_names_ignored_for_other_skin(skin_type: SkinType) -> None:
    assert _run(ProfileFacts(skin_type=skin_type), [_ing("ALCOHOL DENAT.")]).alerts == []


@pytest.mark.parametrize(
    "profile",
    [
        ProfileFacts(skin_type=SkinType.OILY),
        ProfileFacts(health_conditions=frozenset({HealthCondition.ACNE_PRONE})),
    ],
)
@pytest.mark.parametrize("locale", ["en", "fr"])
@pytest.mark.parametrize("name", sorted(HEAVY_OCCLUSIVE_NAMES))
def test_occlusives_for_oily_or_acne_prone(profile: ProfileFacts, name: str, locale: str) -> None:
    result = _run(profile, [_ing(name)], locale)
    [alert] = result.alerts
    assert alert.code == AlertCode.SKIN_TYPE_MISMATCH
    assert alert.severity == AlertSeverity.MEDIUM
    assert alert.title == SKIN_TITLE[locale]
    assert result.verdict == Verdict.CAUTION


def test_occlusives_ignored_for_dry_skin() -> None:
    assert _run(ProfileFacts(skin_type=SkinType.DRY), [_ing("PETROLATUM")]).alerts == []


def test_name_matching_is_case_and_space_insensitive() -> None:
    [alert] = _run(PREGNANT, [_ing("  retinol ")]).alerts
    assert alert.code == AlertCode.PREGNANCY_CONTRAINDICATION
    assert alert.ingredient_name == "  retinol "


def test_same_ingredient_twice_gives_one_alert() -> None:
    item = _ing("RETINOL")
    assert len(_run(PREGNANT, [item, item]).alerts) == 1


def test_one_ingredient_can_trigger_two_alert_types() -> None:
    item = _ing("RETINOL")
    profile = ProfileFacts(
        is_pregnant_or_nursing=True, allergy_ingredient_ids=frozenset({item.ingredient_id})
    )
    codes = {alert.code for alert in _run(profile, [item]).alerts}
    assert codes == {AlertCode.PREGNANCY_CONTRAINDICATION, AlertCode.ALLERGY_MATCH}


def test_alerts_sorted_high_first() -> None:
    profile = ProfileFacts(skin_type=SkinType.DRY, is_pregnant_or_nursing=True)
    result = _run(profile, [_ing("ALCOHOL DENAT."), _ing("RETINOL"), _ing("SALICYLIC ACID")])
    severities = [alert.severity for alert in result.alerts]
    assert severities == [AlertSeverity.HIGH, AlertSeverity.HIGH, AlertSeverity.MEDIUM]
    assert [alert.ingredient_name for alert in result.alerts][:2] == ["RETINOL", "SALICYLIC ACID"]
    assert result.verdict == Verdict.AVOID


def test_high_alert_beats_medium_for_verdict() -> None:
    profile = ProfileFacts(skin_type=SkinType.DRY, is_pregnant_or_nursing=True)
    assert _run(profile, [_ing("ALCOHOL DENAT."), _ing("RETINOL")]).verdict == Verdict.AVOID


def test_arabic_falls_back_to_english() -> None:
    [alert] = _run(PREGNANT, [_ing("RETINOL")], "ar").alerts
    assert alert.title == PREGNANCY_TITLE["en"]


def test_unknown_locale_falls_back_to_english() -> None:
    [alert] = _run(PREGNANT, [_ing("RETINOL")], "xx").alerts
    assert alert.title == PREGNANCY_TITLE["en"]
