from scripts.calibrate_scoring import (
    check_monotonicity,
    evaluate_dataset,
    generate_benchmark_items,
    run_calibration,
)

from app.modules.scoring.engine import DEFAULT_SCORING_PARAMS, ScoringParams


def test_monotonicity_checks() -> None:
    # Baseline params must pass monotonicity
    assert check_monotonicity(DEFAULT_SCORING_PARAMS) is True

    # Inverted thresholds should fail
    bad_thresholds = ScoringParams(low_risk_min_score=40, moderate_risk_min_score=60)
    assert check_monotonicity(bad_thresholds) is False


def test_evaluate_and_calibrate_benchmark() -> None:
    items = generate_benchmark_items(30)
    assert len(items) == 30

    metrics = evaluate_dataset(items, DEFAULT_SCORING_PARAMS)
    assert metrics["spearman"] > 0.8
    assert metrics["mae"] < 10.0

    # Short calibration run
    train = items[:20]
    test = items[20:]
    calib_params, report = run_calibration(train, test, max_iter=3)
    assert check_monotonicity(calib_params) is True
    assert "calibrated_train" in report
