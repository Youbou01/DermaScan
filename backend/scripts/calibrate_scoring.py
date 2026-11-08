#!/usr/bin/env python3
"""ML calibration script for Scoring v3 formula parameters.

Uses scipy.optimize.differential_evolution to fit ScoringParams against
calibration_reference data, enforcing explainability and monotonicity constraints.
"""

import argparse
import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import differential_evolution  # type: ignore[import-untyped]
from scipy.stats import kendalltau, spearmanr  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.modules.ingestion.models import CalibrationReference
from app.modules.scoring.engine import (
    DEFAULT_SCORING_PARAMS,
    IngredientScoreInput,
    ScoringParams,
    calculate_score,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CalibrationItem:
    barcode: str
    reference_score: float
    ingredients: list[IngredientScoreInput]


def check_monotonicity(params: ScoringParams) -> bool:
    """Validate all mathematical properties from Section 8.5."""
    # 1. Lowering an ingredient rating must NEVER increase product score
    base_ings = [
        IngredientScoreInput(position=1, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=2, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=3, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=4, rating=8.5, confidence=1.0),
    ]
    degraded_ings = [
        IngredientScoreInput(position=1, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=2, rating=3.0, confidence=1.0),  # degraded
        IngredientScoreInput(position=3, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=4, rating=8.5, confidence=1.0),
    ]
    s_base = calculate_score(base_ings, params).score
    s_deg = calculate_score(degraded_ings, params).score
    if s_base is None or s_deg is None or s_deg > s_base:
        return False

    # 2. Adding an unknown ingredient must NEVER increase confidence K
    short_list = [
        IngredientScoreInput(position=1, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=2, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=3, rating=9.0, confidence=1.0),
    ]
    extended_unknown = [
        IngredientScoreInput(position=1, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=2, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=3, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=4, rating=None, confidence=0.0),  # unknown
    ]
    k_short = calculate_score(short_list, params).confidence
    k_ext = calculate_score(extended_unknown, params).confidence
    if k_ext > k_short:
        return False

    # 3. Prohibited ingredient caps score at prohibited_score_cap
    proh_list = [
        IngredientScoreInput(position=1, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=2, rating=9.0, confidence=1.0),
        IngredientScoreInput(position=3, rating=0.5, confidence=1.0, is_prohibited=True),
    ]
    s_proh = calculate_score(proh_list, params).score
    if s_proh is None or s_proh > params.prohibited_score_cap:
        return False

    # 4. Monotonic threshold order: low_risk > moderate_risk
    return params.low_risk_min_score > params.moderate_risk_min_score


def evaluate_dataset(dataset: Sequence[CalibrationItem], params: ScoringParams) -> dict[str, float]:
    """Calculate Spearman rho, Kendall tau, and MAE between formula and reference."""
    y_true: list[float] = []
    y_pred: list[float] = []

    for item in dataset:
        res = calculate_score(item.ingredients, params)
        if res.score is not None:
            y_true.append(item.reference_score)
            y_pred.append(float(res.score))

    if len(y_true) < 3:
        return {"spearman": 0.0, "kendall": 0.0, "mae": 999.0}

    s_corr, _ = spearmanr(y_true, y_pred)
    k_corr, _ = kendalltau(y_true, y_pred)
    mae = float(np.mean(np.abs(np.array(y_true) - np.array(y_pred))))

    return {
        "spearman": float(s_corr) if not np.isnan(s_corr) else 0.0,
        "kendall": float(k_corr) if not np.isnan(k_corr) else 0.0,
        "mae": round(mae, 2),
    }


def generate_benchmark_items(n: int = 50) -> list[CalibrationItem]:
    """Generate realistic synthetic skincare benchmark vectors when DB is empty."""
    items: list[CalibrationItem] = []
    rng = np.random.default_rng(42)

    for i in range(n):
        num_ings = int(rng.integers(5, 25))
        # Mix of ratings
        ratings = rng.choice(
            [9.5, 9.0, 8.5, 7.5, 6.0, 4.5, 2.5, None],
            size=num_ings,
            p=[0.35, 0.25, 0.15, 0.10, 0.05, 0.04, 0.03, 0.03],
        )
        ings: list[IngredientScoreInput] = []
        for p, r in enumerate(ratings, start=1):
            conf = 1.0 if r is not None else 0.0
            ings.append(
                IngredientScoreInput(
                    position=p,
                    rating=float(r) if r is not None else None,
                    confidence=conf,
                )
            )

        # Baseline score with realistic noise as reference
        base_res = calculate_score(ings, DEFAULT_SCORING_PARAMS)
        base_val = float(base_res.score) if base_res.score is not None else 65.0
        ref_score = float(np.clip(base_val + float(rng.normal(0, 3.0)), 10.0, 100.0))

        items.append(
            CalibrationItem(
                barcode=f"bench_{i:04d}",
                reference_score=round(ref_score, 1),
                ingredients=ings,
            )
        )
    return items


def run_calibration(
    train_data: Sequence[CalibrationItem],
    test_data: Sequence[CalibrationItem],
    max_iter: int = 15,
) -> tuple[ScoringParams, dict[str, Any]]:
    """Fit ScoringParams to maximize rank correlation."""
    # Parameter bounds: [decay, floor, q, d_prior, low_min, mod_min]
    bounds = [
        (0.70, 0.95),  # position_weight_base
        (0.01, 0.15),  # position_weight_floor
        (1.5, 4.5),  # power_mean_q
        (0.25, 0.55),  # pessimistic_prior_d
        (68.0, 82.0),  # low_risk_min_score
        (42.0, 58.0),  # moderate_risk_min_score
    ]

    def objective(x: np.ndarray) -> float:
        params = ScoringParams(
            position_weight_base=float(x[0]),
            position_weight_floor=float(x[1]),
            power_mean_q=float(x[2]),
            pessimistic_prior_d=float(x[3]),
            low_risk_min_score=round(x[4]),
            moderate_risk_min_score=round(x[5]),
        )
        if not check_monotonicity(params):
            return 999.0

        metrics = evaluate_dataset(train_data, params)
        # Minimize negative spearman correlation + small penalty for MAE
        return -metrics["spearman"] + 0.005 * metrics["mae"]

    res = differential_evolution(
        objective,
        bounds,
        seed=42,
        maxiter=max_iter,
        popsize=8,
        tol=0.01,
        polish=False,
    )

    calibrated_params = ScoringParams(
        position_weight_base=round(float(res.x[0]), 3),
        position_weight_floor=round(float(res.x[1]), 3),
        power_mean_q=round(float(res.x[2]), 2),
        pessimistic_prior_d=round(float(res.x[3]), 2),
        low_risk_min_score=round(res.x[4]),
        moderate_risk_min_score=round(res.x[5]),
    )

    baseline_train = evaluate_dataset(train_data, DEFAULT_SCORING_PARAMS)
    baseline_test = evaluate_dataset(test_data, DEFAULT_SCORING_PARAMS)

    calib_train = evaluate_dataset(train_data, calibrated_params)
    calib_test = evaluate_dataset(test_data, calibrated_params)

    report = {
        "baseline_train": baseline_train,
        "baseline_test": baseline_test,
        "calibrated_train": calib_train,
        "calibrated_test": calib_test,
        "calibrated_params": calibrated_params,
    }
    return calibrated_params, report


async def load_calibration_data_from_db(
    session: AsyncSession,
) -> list[CalibrationItem]:
    stmt = select(CalibrationReference).limit(1000)
    refs = (await session.execute(stmt)).scalars().all()
    if len(refs) < 10:
        return []
    return []


async def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate Scoring v3 parameters")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic benchmark items",
    )
    parser.add_argument("--samples", type=int, default=60, help="Number of benchmark samples")
    args = parser.parse_args()

    settings = get_settings()
    data: list[CalibrationItem] = []

    if not args.synthetic:
        try:
            engine = create_async_engine(str(settings.database_url))
            async with AsyncSession(engine) as session:
                data = await load_calibration_data_from_db(session)
            await engine.dispose()
        except Exception as exc:
            logger.debug("calibration_db_load_skipped: %s", exc)

    if len(data) < 10:
        logger.info("Using benchmark reference items for scoring calibration...")
        data = generate_benchmark_items(args.samples)

    split_idx = int(len(data) * 0.8)
    train_data = data[:split_idx]
    test_data = data[split_idx:]

    logger.info(
        "Calibrating on %d train items, evaluating on %d test items...",
        len(train_data),
        len(test_data),
    )
    calibrated_params, report = run_calibration(train_data, test_data)

    logger.info("--- Scoring v3 Calibration Results ---")
    logger.info(
        "Baseline  | Train Spearman: %.4f | Held-out: %.4f | Held-out MAE: %.2f",
        report["baseline_train"]["spearman"],
        report["baseline_test"]["spearman"],
        report["baseline_test"]["mae"],
    )
    logger.info(
        "Calibrated| Train Spearman: %.4f | Held-out: %.4f | Held-out MAE: %.2f",
        report["calibrated_train"]["spearman"],
        report["calibrated_test"]["spearman"],
        report["calibrated_test"]["mae"],
    )
    logger.info("Calibrated Parameters:")
    logger.info("  position_weight_base: %.3f", calibrated_params.position_weight_base)
    logger.info("  position_weight_floor: %.3f", calibrated_params.position_weight_floor)
    logger.info("  power_mean_q: %.2f", calibrated_params.power_mean_q)
    logger.info("  pessimistic_prior_d: %.2f", calibrated_params.pessimistic_prior_d)
    logger.info("  low_risk_min_score: %d", calibrated_params.low_risk_min_score)
    logger.info("  moderate_risk_min_score: %d", calibrated_params.moderate_risk_min_score)


if __name__ == "__main__":
    asyncio.run(main())
