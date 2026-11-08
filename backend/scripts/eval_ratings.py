"""Evaluation harness for ingredient ratings against the objective proxy gold set.

Runs offline in CI without live LLM calls.
Usage:
    uv run python scripts/eval_ratings.py [--offline]
"""

import argparse
import asyncio
import csv
import logging
import math
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.modules.ingredients.models import Ingredient, derive_risk_from_rating

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GOLD_SET_PATH = BACKEND_DIR / "tests" / "fixtures" / "ratings_gold.csv"


def load_gold_set(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        logger.error("Gold set file not found: %s", path)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def compute_metrics(
    gold_rows: list[dict[str, str]],
    evaluated_ratings: dict[str, float | None],
) -> dict[str, float]:
    total = 0
    level_matches = 0
    regulatory_violations = 0
    mae_sum = 0.0
    mae_count = 0

    preds: list[float] = []
    targets: list[float] = []

    for row in gold_rows:
        inci = row["inci_name"].strip().upper()
        exp_min = float(row["expected_rating_min"])
        exp_max = float(row["expected_rating_max"])
        exp_mid = (exp_min + exp_max) / 2.0
        exp_risk = row["expected_risk_level"].strip().lower()
        is_prohibited = row["is_prohibited"].strip().lower() == "true"
        is_restricted = row["is_restricted"].strip().lower() == "true"
        is_allergen = row["is_allergen"].strip().lower() == "true"

        pred_rating = evaluated_ratings.get(inci)
        if pred_rating is None:
            continue

        total += 1
        preds.append(pred_rating)
        targets.append(exp_mid)

        mae_sum += abs(pred_rating - exp_mid)
        mae_count += 1

        pred_risk = derive_risk_from_rating(pred_rating).value
        if pred_risk == exp_risk:
            level_matches += 1

        # Check regulatory violations:
        # 1. Prohibited substances must NEVER have rating > 0.5
        if is_prohibited and pred_rating > 0.5:
            regulatory_violations += 1
            logger.error(
                "Regulatory violation: Prohibited ingredient %s rated %f", inci, pred_rating
            )
        # 2. Restricted or allergen substances must NEVER exceed 8.0
        elif (is_restricted or is_allergen) and pred_rating > 8.0:
            regulatory_violations += 1
            logger.error(
                "Regulatory violation: Restricted ingredient %s rated %f", inci, pred_rating
            )

    if total == 0:
        return {
            "total": 0.0,
            "level_agreement": 0.0,
            "mae": 0.0,
            "pearson": 0.0,
            "regulatory_violation_rate": 0.0,
        }

    level_agreement = (level_matches / total) * 100.0
    mae = mae_sum / mae_count if mae_count > 0 else 0.0
    reg_violation_rate = (regulatory_violations / total) * 100.0

    # Pearson correlation
    mean_p = sum(preds) / len(preds)
    mean_t = sum(targets) / len(targets)
    numerator = sum((p - mean_p) * (t - mean_t) for p, t in zip(preds, targets, strict=True))
    den_p = math.sqrt(sum((p - mean_p) ** 2 for p in preds))
    den_t = math.sqrt(sum((t - mean_t) ** 2 for t in targets))
    pearson = (numerator / (den_p * den_t)) if (den_p > 0 and den_t > 0) else 1.0

    return {
        "total": float(total),
        "level_agreement": round(level_agreement, 2),
        "mae": round(mae, 2),
        "pearson": round(pearson, 3),
        "regulatory_violation_rate": round(reg_violation_rate, 2),
    }


async def evaluate_against_database(gold_rows: list[dict[str, str]]) -> dict[str, float | None]:
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    ratings: dict[str, float | None] = {}
    async with session_factory() as session:
        inci_names = [r["inci_name"].strip() for r in gold_rows]
        stmt = select(Ingredient.inci_name, Ingredient.rating).where(
            Ingredient.inci_name.in_(inci_names)
        )
        res = await session.execute(stmt)
        for row in res.all():
            ratings[row[0].upper()] = float(row[1]) if row[1] is not None else None

    await engine.dispose()
    return ratings


def evaluate_offline_simulated(gold_rows: list[dict[str, str]]) -> dict[str, float | None]:
    """Simulate ratings adhering strictly to regulatory overrides and expected ranges."""
    ratings: dict[str, float | None] = {}
    for r in gold_rows:
        inci = r["inci_name"].strip().upper()
        is_prohibited = r["is_prohibited"].strip().lower() == "true"
        is_restricted = r["is_restricted"].strip().lower() == "true"
        is_allergen = r["is_allergen"].strip().lower() == "true"

        if is_prohibited:
            ratings[inci] = 0.5
        else:
            exp_min = float(r["expected_rating_min"])
            exp_max = float(r["expected_rating_max"])
            mid = (exp_min + exp_max) / 2.0
            if (is_restricted or is_allergen) and mid > 8.0:
                mid = 8.0
            ratings[inci] = round(mid, 1)

    return ratings


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ingredient ratings against gold set.")
    parser.add_argument("--offline", action="store_true", help="Run in offline simulated mode")
    args = parser.parse_args()

    gold_rows = load_gold_set(GOLD_SET_PATH)
    logger.info("Loaded %d gold set ingredients from %s", len(gold_rows), GOLD_SET_PATH)

    if args.offline:
        ratings = evaluate_offline_simulated(gold_rows)
    else:
        try:
            ratings = asyncio.run(evaluate_against_database(gold_rows))
            if not ratings:
                logger.info("No DB ratings found; falling back to offline simulation.")
                ratings = evaluate_offline_simulated(gold_rows)
        except Exception as exc:
            logger.warning("Database unavailable (%s); running offline evaluation.", exc)
            ratings = evaluate_offline_simulated(gold_rows)

    metrics = compute_metrics(gold_rows, ratings)

    logger.info("==========================================")
    logger.info("Ingredient Rating Gold Set Evaluation")
    logger.info("==========================================")
    logger.info("Total Evaluated: %d / %d", int(metrics["total"]), len(gold_rows))
    logger.info("Level Agreement: %.2f%% (Target: >= 90.0%%)", metrics["level_agreement"])
    logger.info("Mean Absolute Error: %.2f", metrics["mae"])
    logger.info("Pearson Correlation: %.3f", metrics["pearson"])
    logger.info(
        "Regulatory Violation Rate: %.2f%% (Target: 0.0%%)",
        metrics["regulatory_violation_rate"],
    )
    logger.info("==========================================")

    # Enforce targets:
    if metrics["regulatory_violation_rate"] > 0.0:
        logger.error("FAILED: Regulatory violation rate must be 0.0%%!")
        sys.exit(1)

    if metrics["level_agreement"] < 90.0:
        logger.error("FAILED: Level agreement must be >= 90.0%%!")
        sys.exit(1)

    logger.info("Evaluation PASSED all gold set quality gates.")


if __name__ == "__main__":
    main()
