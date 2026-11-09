"""Pure domain engine for detecting harmful chemical interactions between products.

Classifies active ingredients into known interaction families and evaluates pairwise
incompatibilities and active over-stacking with localized (EN/FR) explanations and actionable
resolution guidance.
"""

import uuid
from dataclasses import dataclass

from app.modules.routines.schemas import RoutineConflictOut

# Interaction active families and canonical uppercase ingredient tokens
RETINOID_TOKENS: frozenset[str] = frozenset(
    {
        "RETINOL",
        "RETINAL",
        "RETINOIC ACID",
        "ADAPALENE",
        "TRETINOIN",
        "HYDROXYPINACOLONE RETINOATE",
    }
)

AHA_BHA_ACID_TOKENS: frozenset[str] = frozenset(
    {
        "GLYCOLIC ACID",
        "LACTIC ACID",
        "SALICYLIC ACID",
        "MANDELIC ACID",
        "CITRIC ACID",
        "GLUCONOLACTONE",
    }
)

BENZOYL_PEROXIDE_TOKENS: frozenset[str] = frozenset(
    {
        "BENZOYL PEROXIDE",
    }
)

PURE_VITAMIN_C_TOKENS: frozenset[str] = frozenset(
    {
        "ASCORBIC ACID",
        "L-ASCORBIC ACID",
    }
)

PEPTIDE_TOKENS: frozenset[str] = frozenset(
    {
        "COPPER TRIPEPTIDE-1",
        "PALMITOYL TRIPEPTIDE-1",
        "ACETYL HEXAPEPTIDE-8",
    }
)


@dataclass(slots=True, frozen=True)
class ProductActiveProfile:
    """Active ingredient representation of a product in a routine step."""

    product_id: uuid.UUID
    product_name: str
    active_ingredients: tuple[str, ...]
    category_slug: str | None = None


def extract_actives(ingredient_names: list[str], category_slug: str | None = None) -> list[str]:
    """Filters ingredient names to interaction actives.

    Citric acid is a common pH adjuster, so it is an exfoliating active only for
    exfoliant-like product categories. This prevents a false warning for otherwise
    benign formulas such as a cleanser or moisturiser.
    """
    actives: list[str] = []
    seen: set[str] = set()
    contextual_acids = AHA_BHA_ACID_TOKENS - {"CITRIC ACID"}
    if category_slug in {"exfoliant", "serum", "toner"}:
        contextual_acids = AHA_BHA_ACID_TOKENS
    all_known = (
        RETINOID_TOKENS
        | contextual_acids
        | BENZOYL_PEROXIDE_TOKENS
        | PURE_VITAMIN_C_TOKENS
        | PEPTIDE_TOKENS
    )
    for name in ingredient_names:
        upper = name.strip().upper()
        if upper in all_known and upper not in seen:
            seen.add(upper)
            actives.append(upper)
    return actives


def _active_in_family(profile: ProductActiveProfile, family: frozenset[str]) -> str | None:
    """Return the first family member in label order, respecting citric-acid context."""
    active_names = extract_actives(list(profile.active_ingredients), profile.category_slug)
    return next((name for name in active_names if name in family), None)


def detect_routine_conflicts(
    products: list[ProductActiveProfile],
    locale: str = "en",
) -> list[RoutineConflictOut]:
    """Pure domain function that evaluates all pairwise chemical conflicts between products

    in the same routine slot.
    """
    conflicts: list[RoutineConflictOut] = []
    is_fr = str(locale).lower().startswith("fr")
    n = len(products)

    for i in range(n):
        for j in range(i + 1, n):
            prod_a = products[i]
            prod_b = products[j]

            ret_a = _active_in_family(prod_a, RETINOID_TOKENS)
            ret_b = _active_in_family(prod_b, RETINOID_TOKENS)
            acid_a = _active_in_family(prod_a, AHA_BHA_ACID_TOKENS)
            acid_b = _active_in_family(prod_b, AHA_BHA_ACID_TOKENS)
            bpo_a = _active_in_family(prod_a, BENZOYL_PEROXIDE_TOKENS)
            bpo_b = _active_in_family(prod_b, BENZOYL_PEROXIDE_TOKENS)
            vitc_a = _active_in_family(prod_a, PURE_VITAMIN_C_TOKENS)
            vitc_b = _active_in_family(prod_b, PURE_VITAMIN_C_TOKENS)
            pep_a = _active_in_family(prod_a, PEPTIDE_TOKENS)
            pep_b = _active_in_family(prod_b, PEPTIDE_TOKENS)

            # Rule 1: Retinoids + AHA/BHA Acids (High Severity)
            if (ret_a and acid_b) or (acid_a and ret_b):
                ing_a = ret_a or acid_a or ""
                ing_b = acid_b or ret_b or ""
                conflicts.append(
                    RoutineConflictOut(
                        code="retinoid_x_acid",
                        severity="high",
                        product_a_id=prod_a.product_id,
                        product_b_id=prod_b.product_id,
                        product_a_name=prod_a.product_name,
                        product_b_name=prod_b.product_name,
                        ingredient_a=ing_a,
                        ingredient_b=ing_b,
                        title=(
                            "Interaction Rétinoïde + Acide Exfoliant (AHA/BHA)"
                            if is_fr
                            else "Retinoid + Exfoliating Acid (AHA/BHA) Conflict"
                        ),
                        detail=(
                            f"Combiner {ing_a} et {ing_b} dans la même routine augmente fortement l'irritation de la barrière cutanée."
                            if is_fr
                            else f"Layering {ing_a} and {ing_b} in the same routine significantly increases skin barrier irritation and peeling."
                        ),
                        resolution=(
                            "Utilisez ces produits un soir sur deux ou déplacez le tonique exfoliant dans une autre routine."
                            if is_fr
                            else "Use on alternate evenings or move the exfoliating acid to a separate routine."
                        ),
                    )
                )

            # Rule 2: Retinoids + Benzoyl Peroxide (High Severity)
            if (ret_a and bpo_b) or (bpo_a and ret_b):
                ing_a = ret_a or bpo_a or ""
                ing_b = bpo_b or ret_b or ""
                conflicts.append(
                    RoutineConflictOut(
                        code="retinoid_x_bpo",
                        severity="high",
                        product_a_id=prod_a.product_id,
                        product_b_id=prod_b.product_id,
                        product_a_name=prod_a.product_name,
                        product_b_name=prod_b.product_name,
                        ingredient_a=ing_a,
                        ingredient_b=ing_b,
                        title=(
                            "Interaction Rétinoïde + Peroxyde de Benzoyle"
                            if is_fr
                            else "Retinoid + Benzoyl Peroxide Conflict"
                        ),
                        detail=(
                            "Le peroxyde de benzoyle peut oxyder le rétinol et accentuer la sécheresse cutanée."
                            if is_fr
                            else "Benzoyl peroxide oxidizes and deactivates retinoids while compounding skin dryness."
                        ),
                        resolution=(
                            "Appliquez le peroxyde de benzoyle le matin et le rétinol le soir."
                            if is_fr
                            else "Apply benzoyl peroxide in the morning and retinol in the evening."
                        ),
                    )
                )

            # Rule 3: Pure Vitamin C + (Retinoids or AHA/BHA Acids) (Moderate Severity)
            if (vitc_a and (ret_b or acid_b)) or ((ret_a or acid_a) and vitc_b):
                ing_a = vitc_a or ret_a or acid_a or ""
                ing_b = ret_b or acid_b or vitc_b or ""
                conflicts.append(
                    RoutineConflictOut(
                        code="vitc_x_active",
                        severity="moderate",
                        product_a_id=prod_a.product_id,
                        product_b_id=prod_b.product_id,
                        product_a_name=prod_a.product_name,
                        product_b_name=prod_b.product_name,
                        ingredient_a=ing_a,
                        ingredient_b=ing_b,
                        title=(
                            "Interaction Vitamine C Pure + Actif Intense"
                            if is_fr
                            else "Pure Vitamin C + Intensive Active Overlap"
                        ),
                        detail=(
                            f"Superposer {ing_a} et {ing_b} peut déséquilibrer le pH et provoquer des picotements."
                            if is_fr
                            else f"Layering {ing_a} with {ing_b} may cause pH mismatch and heightened stinging."
                        ),
                        resolution=(
                            "Gardez la Vitamine C pour le matin et les rétinoïdes ou acides pour le soir."
                            if is_fr
                            else "Keep Vitamin C in your Morning routine and retinoids or acids in your Evening routine."
                        ),
                    )
                )

            # Rule 4: AHA/BHA Acids + Peptides (Moderate Severity)
            if (acid_a and pep_b) or (pep_a and acid_b):
                ing_a = acid_a or pep_a or ""
                ing_b = pep_b or acid_b or ""
                conflicts.append(
                    RoutineConflictOut(
                        code="acid_x_peptide",
                        severity="moderate",
                        product_a_id=prod_a.product_id,
                        product_b_id=prod_b.product_id,
                        product_a_name=prod_a.product_name,
                        product_b_name=prod_b.product_name,
                        ingredient_a=ing_a,
                        ingredient_b=ing_b,
                        title=(
                            "Interaction Acide Exfoliant + Peptides"
                            if is_fr
                            else "Exfoliating Acid + Peptide Sensitivity"
                        ),
                        detail=(
                            f"Les acides à pH bas ({ing_a}) peuvent dégrader les peptides ({ing_b}) et réduire leur efficacité."
                            if is_fr
                            else f"Low-pH acids ({ing_a}) can hydrolyze peptides ({ing_b}), reducing their efficacy."
                        ),
                        resolution=(
                            "Utilisez les peptides le matin et les acides exfoliants le soir."
                            if is_fr
                            else "Use peptides in your morning routine and exfoliating acids in the evening."
                        ),
                    )
                )

            # Rule 5: Duplicate Retinoids or Duplicate Acids (Over-Stacking)
            if ret_a and ret_b:
                conflicts.append(
                    RoutineConflictOut(
                        code="duplicate_retinoid",
                        severity="high",
                        product_a_id=prod_a.product_id,
                        product_b_id=prod_b.product_id,
                        product_a_name=prod_a.product_name,
                        product_b_name=prod_b.product_name,
                        ingredient_a=ret_a,
                        ingredient_b=ret_b,
                        title=(
                            "Cumul Excessif de Rétinoïdes"
                            if is_fr
                            else "Retinoid Over-Stacking Conflict"
                        ),
                        detail=(
                            f"Deux soins contenant des rétinoïdes ({ret_a} et {ret_b}) sont superposés, créant un risque majeur d'irritation."
                            if is_fr
                            else f"Multiple products containing retinoids ({ret_a} and {ret_b}) are layered in the same routine, creating a heightened risk of irritation."
                        ),
                        resolution=(
                            "Choisissez un seul produit rétinoïde par routine."
                            if is_fr
                            else "Choose a single retinoid product per routine to protect your skin barrier."
                        ),
                    )
                )
            elif acid_a and acid_b:
                conflicts.append(
                    RoutineConflictOut(
                        code="duplicate_acid",
                        severity="moderate",
                        product_a_id=prod_a.product_id,
                        product_b_id=prod_b.product_id,
                        product_a_name=prod_a.product_name,
                        product_b_name=prod_b.product_name,
                        ingredient_a=acid_a,
                        ingredient_b=acid_b,
                        title=(
                            "Cumul d'Acides Exfoliants"
                            if is_fr
                            else "Multiple Exfoliating Acids Over-Stacking"
                        ),
                        detail=(
                            f"Superposer plusieurs acides exfoliants ({acid_a} et {acid_b}) risque de sur-exfolier l'épiderme."
                            if is_fr
                            else f"Layering multiple exfoliating acids ({acid_a} and {acid_b}) risks over-exfoliation and barrier compromise."
                        ),
                        resolution=(
                            "Alternez vos exfoliants sur différents jours."
                            if is_fr
                            else "Alternate your exfoliating acids on different days."
                        ),
                    )
                )

    return conflicts
