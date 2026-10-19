import csv
from pathlib import Path

SEED_FILE = Path(__file__).resolve().parents[2] / "src/app/modules/ingredients/seed_data.csv"


def validate_seed_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen_names: set[str] = set()

    for idx, row in enumerate(rows, start=2):
        inci = (row.get("inci_name") or "").strip()
        risk = (row.get("risk_level") or "").strip().lower()
        source_ref = (row.get("source_ref") or "").strip()
        rationale_en = (row.get("rationale_en") or "").strip()

        if not inci:
            errors.append(f"Row {idx}: Missing inci_name")
        elif inci.lower() in seen_names:
            errors.append(f"Row {idx}: Duplicate inci_name '{inci}'")
        else:
            seen_names.add(inci.lower())

        if risk not in {"low", "moderate", "high"}:
            errors.append(f"Row {idx} ({inci}): Invalid risk_level '{risk}'")

        if risk in {"moderate", "high"}:
            if not source_ref:
                errors.append(f"Row {idx} ({inci}): risk_level='{risk}' requires source_ref")
            if not rationale_en:
                errors.append(f"Row {idx} ({inci}): risk_level='{risk}' requires rationale_en")

    return errors


def test_curated_seed_file_passes_ci_validation() -> None:
    assert SEED_FILE.exists(), f"Missing seed file at {SEED_FILE}"
    with open(SEED_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0, "Seed file cannot be empty"
    errors = validate_seed_rows(rows)
    assert errors == [], "Seed validation failed:\n" + "\n".join(errors)


def test_validator_rejects_moderate_or_high_without_source_or_rationale() -> None:
    bad_rows = [
        {
            "inci_name": "TestHigh",
            "risk_level": "high",
            "source_ref": "",
            "rationale_en": "Has rationale",
        },
        {
            "inci_name": "TestMod",
            "risk_level": "moderate",
            "source_ref": "SCCS/123",
            "rationale_en": "",
        },
    ]
    errors = validate_seed_rows(bad_rows)
    assert len(errors) == 2
