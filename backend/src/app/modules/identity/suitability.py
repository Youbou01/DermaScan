"""Pure, deterministic suitability engine (no database, no LLM: ADR-0012).

It takes plain facts about the user and the matched ingredients of one product and returns the
`SuitabilityOut` the mobile app shows. The service layer gathers the facts.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.i18n import pick_translation
from app.modules.identity.enums import AlertCode, AlertSeverity, SkinType, Verdict
from app.modules.identity.schemas import HealthCondition, RiskAlertOut, SuitabilityOut

PREGNANCY_UNSAFE_NAMES = frozenset(
    {
        "RETINOL",
        "RETINAL",
        "RETINOIC ACID",
        "RETINYL PALMITATE",
        "HYDROXYPINACOLONE RETINOATE",
        "HYDROQUINONE",
        "SALICYLIC ACID",
        "BENZOYL PEROXIDE",
    }
)
DRYING_NAMES = frozenset({"ALCOHOL DENAT.", "SODIUM LAURYL SULFATE"})
# Dev 1's choice: the sprint names no heavy occlusives, so this short list needs review.
HEAVY_OCCLUSIVE_NAMES = frozenset({"PETROLATUM", "PARAFFINUM LIQUIDUM", "LANOLIN"})
_SENSITIVE_CONDITIONS = frozenset({HealthCondition.ECZEMA, HealthCondition.ROSACEA})

# key -> locale -> (title, detail); "{name}" is replaced by the ingredient name.
_MESSAGES: dict[str, dict[str, tuple[str, str]]] = {
    "pregnancy": {
        "en": (
            "Not recommended during pregnancy",
            "Contains {name}, which is contraindicated during pregnancy and nursing.",
        ),
        "fr": (
            "Déconseillé pendant la grossesse",
            "Contient {name}, contre-indiqué pendant la grossesse et l'allaitement.",
        ),
    },
    "allergy": {
        "en": (
            "Matches your allergy or sensitivity profile",
            "Contains {name}, which matches your declared allergies or sensitivities.",
        ),
        "fr": (
            "Correspond à votre profil d'allergie ou de sensibilité",
            "Contient {name}, qui correspond à vos allergies ou sensibilités déclarées.",
        ),
    },
    "blacklisted": {
        "en": ("On your blacklist", "Contains {name}, an ingredient you blacklisted."),
        "fr": ("Dans votre liste noire", "Contient {name}, un ingrédient de votre liste noire."),
    },
    "drying": {
        "en": (
            "May not suit your skin type",
            "Contains {name}, which can be drying or irritating for dry or sensitive skin.",
        ),
        "fr": (
            "Peut ne pas convenir à votre type de peau",
            "Contient {name}, qui peut dessécher ou irriter les peaux sèches ou sensibles.",
        ),
    },
    "occlusive": {
        "en": (
            "May not suit your skin type",
            "Contains {name}, a heavy occlusive that can clog pores on oily or acne-prone skin.",
        ),
        "fr": (
            "Peut ne pas convenir à votre type de peau",
            "Contient {name}, un occlusif riche qui peut obstruer les pores des peaux "
            "grasses ou à tendance acnéique.",
        ),
    },
}


@dataclass(frozen=True)
class ProfileFacts:
    """What the engine needs to know about the user."""

    skin_type: SkinType | None = None
    is_pregnant_or_nursing: bool = False
    health_conditions: frozenset[HealthCondition] = frozenset()
    allergy_ingredient_ids: frozenset[uuid.UUID] = frozenset()
    blacklisted_ingredient_ids: frozenset[uuid.UUID] = frozenset()
    product_is_blacklisted: bool = False


@dataclass(frozen=True)
class IngredientFacts:
    """One matched ingredient of the product. Unmatched ones are never passed in."""

    ingredient_id: uuid.UUID
    name: str
    is_prohibited: bool = False
    is_allergen: bool = False


def evaluate_suitability(
    product_id: uuid.UUID,
    profile: ProfileFacts,
    ingredients: Sequence[IngredientFacts],
    locale: str,
) -> SuitabilityOut:
    """Check one product against one profile. Same input, same output, no side effects."""
    sensitive_profile = profile.skin_type == SkinType.SENSITIVE or bool(
        profile.health_conditions & _SENSITIVE_CONDITIONS
    )
    drying_risk = profile.skin_type in (SkinType.DRY, SkinType.SENSITIVE)
    oily_risk = profile.skin_type == SkinType.OILY or (
        HealthCondition.ACNE_PRONE in profile.health_conditions
    )

    alerts: list[RiskAlertOut] = []
    seen: set[tuple[AlertCode, uuid.UUID]] = set()

    def add(key: str, code: AlertCode, severity: AlertSeverity, item: IngredientFacts) -> None:
        if (code, item.ingredient_id) in seen:
            return
        seen.add((code, item.ingredient_id))
        table = _MESSAGES[key]
        title, detail = pick_translation(table, locale) or table["en"]
        alerts.append(
            RiskAlertOut(
                code=code,
                severity=severity,
                ingredient_name=item.name,
                title=title,
                detail=detail.format(name=item.name),
            )
        )

    for item in ingredients:
        name = item.name.strip().upper()
        if profile.is_pregnant_or_nursing and (
            name in PREGNANCY_UNSAFE_NAMES or item.is_prohibited
        ):
            add("pregnancy", AlertCode.PREGNANCY_CONTRAINDICATION, AlertSeverity.HIGH, item)
        if item.ingredient_id in profile.allergy_ingredient_ids or (
            item.is_allergen and sensitive_profile
        ):
            add("allergy", AlertCode.ALLERGY_MATCH, AlertSeverity.HIGH, item)
        if item.ingredient_id in profile.blacklisted_ingredient_ids:
            add("blacklisted", AlertCode.BLACKLISTED, AlertSeverity.HIGH, item)
        if drying_risk and name in DRYING_NAMES:
            add("drying", AlertCode.SKIN_TYPE_MISMATCH, AlertSeverity.MEDIUM, item)
        if oily_risk and name in HEAVY_OCCLUSIVE_NAMES:
            add("occlusive", AlertCode.SKIN_TYPE_MISMATCH, AlertSeverity.MEDIUM, item)

    alerts.sort(key=lambda alert: alert.severity != AlertSeverity.HIGH)  # stable: high first
    is_blacklisted = profile.product_is_blacklisted or any(
        alert.code == AlertCode.BLACKLISTED for alert in alerts
    )
    if is_blacklisted or any(alert.severity == AlertSeverity.HIGH for alert in alerts):
        verdict = Verdict.AVOID
    elif alerts:
        verdict = Verdict.CAUTION
    else:
        verdict = Verdict.SUITABLE
    return SuitabilityOut(
        product_id=product_id,
        suits_profile=verdict == Verdict.SUITABLE,
        verdict=verdict,
        has_risk_alert=bool(alerts) or is_blacklisted,
        is_blacklisted=is_blacklisted,
        alerts=alerts,
    )
