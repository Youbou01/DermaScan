from pathlib import Path

from scripts.eval_ratings import compute_metrics, evaluate_offline_simulated, load_gold_set

GOLD_SET_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "ratings_gold.csv"


def test_gold_set_fixture_validity() -> None:
    rows = load_gold_set(GOLD_SET_PATH)
    assert len(rows) >= 150

    for row in rows:
        assert "inci_name" in row
        assert float(row["expected_rating_min"]) <= float(row["expected_rating_max"])
        assert row["expected_risk_level"] in ("low", "moderate", "high")


def test_eval_metrics_against_simulated_ratings() -> None:
    rows = load_gold_set(GOLD_SET_PATH)
    simulated = evaluate_offline_simulated(rows)
    metrics = compute_metrics(rows, simulated)

    assert metrics["total"] == len(rows)
    assert metrics["regulatory_violation_rate"] == 0.0
    assert metrics["level_agreement"] >= 90.0
    assert metrics["pearson"] > 0.85
