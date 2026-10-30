import asyncio
import csv
import logging
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.core.enums import RiskLevel
from app.modules.ingredients.enums import RatingSource, ReviewStatus
from app.modules.ingredients.models import (
    Ingredient,
    IngredientAlias,
    IngredientTranslation,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_CSV_PATH = BACKEND_DIR / "src/app/modules/ingredients/seed_data.csv"


def normalize_string(text: str) -> str:
    if not text:
        return ""
    lower = text.lower()
    cleaned = re.sub(r"[^\w\s]", "", lower)
    return re.sub(r"\s+", " ", cleaned).strip()


async def seed_ingredients() -> None:
    if not SEED_CSV_PATH.exists():
        logger.error("Seed file not found at %s", SEED_CSV_PATH)
        return

    logger.info("Loading ingredient seeds from %s", SEED_CSV_PATH)
    with open(SEED_CSV_PATH, encoding="utf-8") as f:  # noqa: ASYNC230
        reader = list(csv.DictReader(f))

    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    count = 0
    async with session_factory() as db:
        for row in reader:
            inci = row["inci_name"].strip()
            risk_str = row.get("risk_level", "unknown").strip().lower()
            risk_level = RiskLevel(risk_str)
            source_ref = row.get("source_ref", "").strip() or None
            rationale_en = row.get("rationale_en", "").strip()
            rationale_fr = row.get("rationale_fr", "").strip()
            raw_aliases = row.get("aliases", "").strip()

            res = await db.execute(select(Ingredient).where(Ingredient.inci_name == inci))
            ingredient = res.scalar_one_or_none()

            if not ingredient:
                ingredient = Ingredient(
                    inci_name=inci,
                    risk_level=risk_level,
                    source_ref=source_ref,
                    rating_source=RatingSource.CURATED,
                    review_status=ReviewStatus.APPROVED,
                )
                db.add(ingredient)
                await db.flush()
            else:
                ingredient.risk_level = risk_level
                ingredient.source_ref = source_ref
                ingredient.rating_source = RatingSource.CURATED
                ingredient.review_status = ReviewStatus.APPROVED
                await db.flush()

            all_alias_names = [inci]
            if raw_aliases:
                all_alias_names.extend([a.strip() for a in raw_aliases.split("|") if a.strip()])

            for alias_name in all_alias_names:
                norm = normalize_string(alias_name)
                alias_res = await db.execute(
                    select(IngredientAlias).where(IngredientAlias.normalized_alias == norm)
                )
                existing_alias = alias_res.scalar_one_or_none()

                if not existing_alias:
                    db.add(
                        IngredientAlias(
                            ingredient_id=ingredient.id,
                            alias=alias_name,
                            normalized_alias=norm,
                        )
                    )

            if rationale_en:
                trans_res = await db.execute(
                    select(IngredientTranslation).where(
                        IngredientTranslation.ingredient_id == ingredient.id,
                        IngredientTranslation.locale == "en",
                    )
                )
                en_trans = trans_res.scalar_one_or_none()
                if not en_trans:
                    db.add(
                        IngredientTranslation(
                            ingredient_id=ingredient.id,
                            locale="en",
                            rationale=rationale_en,
                        )
                    )
                else:
                    en_trans.rationale = rationale_en

            if rationale_fr:
                trans_res_fr = await db.execute(
                    select(IngredientTranslation).where(
                        IngredientTranslation.ingredient_id == ingredient.id,
                        IngredientTranslation.locale == "fr",
                    )
                )
                fr_trans = trans_res_fr.scalar_one_or_none()
                if not fr_trans:
                    db.add(
                        IngredientTranslation(
                            ingredient_id=ingredient.id,
                            locale="fr",
                            rationale=rationale_fr,
                        )
                    )
                else:
                    fr_trans.rationale = rationale_fr

            count += 1

        await db.commit()
        logger.info(
            "Successfully seeded %d ingredients idempotently into PostgreSQL.",
            count,
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_ingredients())
