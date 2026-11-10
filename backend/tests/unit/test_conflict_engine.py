import uuid

from app.modules.routines.conflict_engine import (
    ProductActiveProfile,
    detect_routine_conflicts,
    extract_actives,
)


def test_extract_actives_filters_known_actives() -> None:
    ingredients = [
        "Aqua",
        "Glycerin",
        "Retinol",
        "Glycolic Acid",
        "Phenoxyethanol",
        "Palmitoyl Tripeptide-1",
    ]
    actives = extract_actives(ingredients)
    assert actives == ["RETINOL", "GLYCOLIC ACID", "PALMITOYL TRIPEPTIDE-1"]


def test_conflict_retinoid_x_acid_en_and_fr() -> None:
    prod_a = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Retinol 0.5% Serum",
        active_ingredients=("RETINOL",),
    )
    prod_b = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Glycolic 7% Toner",
        active_ingredients=("GLYCOLIC ACID",),
    )

    conflicts_en = detect_routine_conflicts([prod_a, prod_b], locale="en")
    assert len(conflicts_en) == 1
    c_en = conflicts_en[0]
    assert c_en.code == "retinoid_x_acid"
    assert c_en.severity == "high"
    assert "Retinoid + Exfoliating Acid" in c_en.title
    assert "RETINOL" in c_en.detail
    assert "GLYCOLIC ACID" in c_en.detail

    conflicts_fr = detect_routine_conflicts([prod_a, prod_b], locale="fr")
    assert len(conflicts_fr) == 1
    c_fr = conflicts_fr[0]
    assert c_fr.code == "retinoid_x_acid"
    assert "Interaction Rétinoïde + Acide Exfoliant" in c_fr.title


def test_conflict_retinoid_x_benzoyl_peroxide() -> None:
    prod_a = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Retinoid Treatment",
        active_ingredients=("TRETINOIN",),
    )
    prod_b = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Acne Cleanser",
        active_ingredients=("BENZOYL PEROXIDE",),
    )

    conflicts = detect_routine_conflicts([prod_a, prod_b], locale="en")
    assert len(conflicts) == 1
    assert conflicts[0].code == "retinoid_x_bpo"
    assert conflicts[0].severity == "high"


def test_conflict_vitc_x_retinoid_and_acid() -> None:
    vit_c = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Vitamin C 15% Serum",
        active_ingredients=("ASCORBIC ACID",),
    )
    salicylic = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="BHA 2% Liquid",
        active_ingredients=("SALICYLIC ACID",),
    )

    conflicts = detect_routine_conflicts([vit_c, salicylic], locale="en")
    assert len(conflicts) == 1
    assert conflicts[0].code == "vitc_x_active"
    assert conflicts[0].severity == "moderate"


def test_conflict_acid_x_peptide() -> None:
    acid = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Lactic Acid 10%",
        active_ingredients=("LACTIC ACID",),
    )
    peptide = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Multi-Peptide Serum",
        active_ingredients=("COPPER TRIPEPTIDE-1",),
    )

    conflicts = detect_routine_conflicts([acid, peptide], locale="en")
    assert len(conflicts) == 1
    assert conflicts[0].code == "acid_x_peptide"
    assert conflicts[0].severity == "moderate"


def test_conflict_active_over_stacking_duplicate_retinoids() -> None:
    ret1 = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Night Retinol",
        active_ingredients=("RETINOL",),
    )
    ret2 = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Retinal Treatment Cream",
        active_ingredients=("RETINAL",),
    )

    conflicts = detect_routine_conflicts([ret1, ret2], locale="en")
    assert len(conflicts) == 1
    assert conflicts[0].code == "duplicate_retinoid"
    assert conflicts[0].severity == "high"


def test_zero_conflicts_for_benign_routine() -> None:
    cleanser = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Hydrating Cleanser",
        active_ingredients=(),  # Glycerin / Hyaluronic Acid only
    )
    moisturizer = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Ceramide Barrier Cream",
        active_ingredients=(),  # Ceramides, Cholesterol
    )
    sunscreen = ProductActiveProfile(
        product_id=uuid.uuid4(),
        product_name="Mineral SPF 50",
        active_ingredients=(),  # Zinc Oxide
    )

    conflicts = detect_routine_conflicts([cleanser, moisturizer, sunscreen], locale="en")
    assert conflicts == []
