"""Download and import official EU CosIng cosmetic ingredient inventory and annexes."""

import asyncio
import csv
import logging
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

# ruff: noqa: E402
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.core.enums import RiskLevel
from app.modules.ingredients.enums import AliasSource, RatingSource, ReviewStatus
from app.modules.ingredients.models import Ingredient, IngredientAlias, IngredientTranslation
from app.modules.ingredients.normalizer import normalize

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = BACKEND_DIR / "data" / "cosing"
SEED_CSV_PATH = BACKEND_DIR / "src/app/modules/ingredients/seed_data.csv"

INVENTORY_URL = (
    "https://raw.githubusercontent.com/openfoodfacts/openbeautyfacts/master/cosing/"
    "COSING_Ingredients-Fragrance.Inventory_v2.csv"
)
ANNEX_II_URL = (
    "https://raw.githubusercontent.com/openfoodfacts/openbeautyfacts/master/cosing/"
    "COSING_Annex.II_v2.csv"
)
ANNEX_III_URL = (
    "https://raw.githubusercontent.com/openfoodfacts/openbeautyfacts/master/cosing/"
    "COSING_Annex.III_v2.csv"
)

EU_FRAGRANCE_ALLERGENS = {
    "AMYL CINNAMAL",
    "BENZYL ALCOHOL",
    "CINNAMYL ALCOHOL",
    "CITRAL",
    "EUGENOL",
    "HYDROXYCITRONELLAL",
    "ISOEUGENOL",
    "AMYLCINNAMYL ALCOHOL",
    "BENZYL SALICYLATE",
    "CINNAMAL",
    "COUMARIN",
    "GERANIOL",
    "HYDROXYISOHEXYL 3-CYCLOHEXENE CARBOXALDEHYDE",
    "ANISE ALCOHOL",
    "BENZYL CINNAMATE",
    "FARNESOL",
    "BUTYLPHENYL METHYLPROPIONAL",
    "LINALOOL",
    "BENZYL BENZOATE",
    "CITRONELLOL",
    "HEXYL CINNAMAL",
    "LIMONENE",
    "METHYL 2-OCTYNOATE",
    "ALPHA-ISOMETHYL IONONE",
    "EVERNIA PRUNASTRI EXTRACT",
    "EVERNIA FURFURACEA EXTRACT",
}


def read_cached_file(path: Path) -> str | None:
    if path.exists() and path.stat().st_size > 1000:
        return path.read_text(encoding="utf-8", errors="ignore")
    return None


def write_cached_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


async def fetch_or_read_cached(client: httpx.AsyncClient, url: str, filename: str) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    local_path = DATA_DIR / filename
    cached = await asyncio.to_thread(read_cached_file, local_path)
    if cached is not None:
        logger.info("Using cached CosIng file: %s", local_path)
        return cached

    logger.info("Downloading %s ...", url)
    resp = await client.get(url, timeout=60.0)
    resp.raise_for_status()
    text = resp.text
    await asyncio.to_thread(write_cached_file, local_path, text)
    return text


def parse_annex_ii(csv_text: str) -> set[str]:
    """Parse Annex II prohibited substances."""
    prohibited: set[str] = set()
    lines = csv_text.splitlines()
    header_idx = -1
    for idx, line in enumerate(lines):
        if "Reference Number" in line or "Chemical name" in line:
            header_idx = idx
            break

    if header_idx == -1:
        return prohibited

    reader = csv.DictReader(lines[header_idx:])
    for row in reader:
        raw_names = row.get("Identified INGREDIENTS or substances e.g.", "") or ""
        chem_name = row.get("Chemical name / INN", "") or ""

        for part in raw_names.split(";"):
            cleaned = part.replace("(*)", "").strip().upper()
            if cleaned:
                prohibited.add(cleaned)
        if chem_name:
            prohibited.add(chem_name.strip().upper())

    logger.info("Parsed %d prohibited substances from Annex II", len(prohibited))
    return prohibited


def parse_annex_iii(csv_text: str) -> set[str]:
    """Parse Annex III restricted substances."""
    restricted: set[str] = set()
    lines = csv_text.splitlines()
    header_idx = -1
    for idx, line in enumerate(lines):
        if "Reference number" in line or "Reference Number" in line:
            header_idx = idx
            break

    if header_idx == -1:
        return restricted

    reader = csv.DictReader(lines[header_idx:])
    for row in reader:
        glossary = row.get("Name of Common Ingredients Glossary", "") or ""
        raw_names = row.get("Identified INGREDIENTS or substances e.g.", "") or ""
        if glossary:
            restricted.add(glossary.strip().upper())
        for part in raw_names.split(";"):
            cleaned = part.replace("(*)", "").strip().upper()
            if cleaned:
                restricted.add(cleaned)

    logger.info("Parsed %d restricted substances from Annex III", len(restricted))
    return restricted


async def import_cosing_inventory(
    db: AsyncSession,
    inventory_text: str,
    prohibited_names: set[str],
    restricted_names: set[str],
) -> int:
    lines = inventory_text.splitlines()
    header_idx = -1
    for idx, line in enumerate(lines):
        if line.startswith("COSING Ref No"):
            header_idx = idx
            break

    if header_idx == -1:
        logger.error("Could not find 'COSING Ref No' header in inventory file")
        return 0

    reader = csv.DictReader(lines[header_idx:])

    # Load existing ingredients and aliases to avoid duplicates
    existing_inci_res = await db.execute(select(Ingredient.inci_name, Ingredient.id))
    existing_by_inci: dict[str, uuid.UUID] = {row[0]: row[1] for row in existing_inci_res.all()}

    existing_aliases_res = await db.execute(select(IngredientAlias.normalized_alias))
    known_normalized_aliases: set[str] = {row[0] for row in existing_aliases_res.all()}

    count = 0
    batch_size = 500
    pending_ingredients: list[Ingredient] = []
    pending_aliases: list[IngredientAlias] = []

    for row in reader:
        cosing_ref = row.get("COSING Ref No", "").strip()
        inci = row.get("INCI name", "").strip()
        if not inci:
            continue

        cas = row.get("CAS No", "").strip() or None
        fn_raw = row.get("Function", "").strip()
        functions = [f.strip().lower() for f in fn_raw.split(",") if f.strip()] if fn_raw else None
        restr_field = row.get("Restriction", "").strip().upper()

        inci_upper = inci.upper()
        is_proh = (
            inci_upper in prohibited_names or "II/" in restr_field or restr_field.startswith("II ")
        )
        is_restr = (
            inci_upper in restricted_names
            or any(f"{annex}/" in restr_field for annex in ("III", "IV", "V", "VI"))
            or is_proh
        )
        is_allg = inci_upper in EU_FRAGRANCE_ALLERGENS

        source_ref: str | None
        rating: Decimal | None
        if is_proh:
            rating = Decimal("0.5")
            risk_level = RiskLevel.HIGH
            source_ref = "EU CosIng Annex II (Prohibited)"
            rating_source = RatingSource.REGULATORY
        else:
            rating = None
            risk_level = RiskLevel.UNKNOWN
            source_ref = "EU CosIng Annex III (Restricted)" if is_restr else None
            rating_source = RatingSource.UNRATED

        norm_inci = normalize(inci)
        if not norm_inci:
            continue

        if inci in existing_by_inci:
            continue  # Already seeded or imported

        ing = Ingredient(
            inci_name=inci,
            risk_level=risk_level,
            source_ref=source_ref,
            rating=rating,
            rating_source=rating_source,
            cosing_id=cosing_ref or None,
            cas=cas,
            functions=functions,
            is_prohibited=is_proh,
            is_restricted=is_restr,
            is_allergen=is_allg,
            review_status=ReviewStatus.AUTO,
        )
        pending_ingredients.append(ing)

        # Primary alias
        if norm_inci not in known_normalized_aliases:
            known_normalized_aliases.add(norm_inci)
            pending_aliases.append(
                IngredientAlias(
                    ingredient=ing,
                    alias=inci,
                    normalized_alias=norm_inci,
                    source=AliasSource.COSING,
                )
            )

        # Synonyms / INN / Chem description
        synonyms = [
            row.get("INN name", "").strip(),
            row.get("Ph. Eur. Name", "").strip(),
        ]
        for syn in synonyms:
            if not syn:
                continue
            norm_syn = normalize(syn)
            if norm_syn and norm_syn not in known_normalized_aliases:
                known_normalized_aliases.add(norm_syn)
                pending_aliases.append(
                    IngredientAlias(
                        ingredient=ing,
                        alias=syn,
                        normalized_alias=norm_syn,
                        source=AliasSource.COSING,
                    )
                )

        count += 1
        existing_by_inci[inci] = ing.id

        if len(pending_ingredients) >= batch_size:
            db.add_all(pending_ingredients)
            db.add_all(pending_aliases)
            await db.flush()
            pending_ingredients.clear()
            pending_aliases.clear()

    if pending_ingredients:
        db.add_all(pending_ingredients)
        db.add_all(pending_aliases)
        await db.flush()

    await db.commit()
    logger.info("Imported %d new CosIng ingredients into database", count)
    return count


async def load_seed_data(db: AsyncSession) -> int:
    """Preserve and load seed_data.csv with rating_source = curated."""
    if not SEED_CSV_PATH.exists():
        logger.warning("seed_data.csv not found at %s", SEED_CSV_PATH)
        return 0

    content = await asyncio.to_thread(SEED_CSV_PATH.read_text, "utf-8")
    reader = list(csv.DictReader(content.splitlines()))

    existing_aliases_res = await db.execute(select(IngredientAlias.normalized_alias))
    known_aliases: set[str] = {row[0] for row in existing_aliases_res.all()}

    count = 0
    for row in reader:
        inci = row["inci_name"].strip()
        risk_str = row.get("risk_level", "unknown").strip().lower()
        risk_level = RiskLevel(risk_str)
        source_ref = row.get("source_ref", "").strip() or None
        rationale_en = row.get("rationale_en", "").strip()
        rationale_fr = row.get("rationale_fr", "").strip()
        raw_aliases = row.get("aliases", "").strip()

        if risk_level == RiskLevel.LOW:
            rating = Decimal("9.0")
        elif risk_level == RiskLevel.MODERATE:
            rating = Decimal("5.5")
        elif risk_level == RiskLevel.HIGH:
            rating = Decimal("2.0")
        else:
            rating = None

        res = await db.execute(select(Ingredient).where(Ingredient.inci_name == inci))
        ing = res.scalar_one_or_none()
        if not ing:
            ing = Ingredient(
                inci_name=inci,
                risk_level=risk_level,
                source_ref=source_ref,
                rating=rating,
                rating_confidence=Decimal("1.0"),
                rating_source=RatingSource.CURATED,
                review_status=ReviewStatus.APPROVED,
            )
            db.add(ing)
            await db.flush()
        else:
            ing.risk_level = risk_level
            ing.source_ref = source_ref
            ing.rating = rating
            ing.rating_confidence = Decimal("1.0")
            ing.rating_source = RatingSource.CURATED
            ing.review_status = ReviewStatus.APPROVED
            await db.flush()

        all_aliases = [inci]
        if raw_aliases:
            all_aliases.extend([a.strip() for a in raw_aliases.split("|") if a.strip()])

        for a_name in all_aliases:
            norm = normalize(a_name)
            if norm and norm not in known_aliases:
                known_aliases.add(norm)
                db.add(
                    IngredientAlias(
                        ingredient_id=ing.id,
                        alias=a_name,
                        normalized_alias=norm,
                        source=AliasSource.SEED,
                    )
                )

        if rationale_en:
            trans_res = await db.execute(
                select(IngredientTranslation).where(
                    IngredientTranslation.ingredient_id == ing.id,
                    IngredientTranslation.locale == "en",
                )
            )
            trans = trans_res.scalar_one_or_none()
            if not trans:
                db.add(
                    IngredientTranslation(
                        ingredient_id=ing.id,
                        locale="en",
                        rationale=rationale_en,
                    )
                )
            else:
                trans.rationale = rationale_en

        if rationale_fr:
            trans_res_fr = await db.execute(
                select(IngredientTranslation).where(
                    IngredientTranslation.ingredient_id == ing.id,
                    IngredientTranslation.locale == "fr",
                )
            )
            trans_fr = trans_res_fr.scalar_one_or_none()
            if not trans_fr:
                db.add(
                    IngredientTranslation(
                        ingredient_id=ing.id,
                        locale="fr",
                        rationale=rationale_fr,
                    )
                )
            else:
                trans_fr.rationale = rationale_fr

        count += 1

    await db.commit()
    logger.info("Loaded %d curated seed ingredients from %s", count, SEED_CSV_PATH)
    return count


async def main() -> None:
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with httpx.AsyncClient() as client:
        inv_text = await fetch_or_read_cached(
            client, INVENTORY_URL, "COSING_Ingredients-Fragrance.Inventory_v2.csv"
        )
        annex2_text = await fetch_or_read_cached(client, ANNEX_II_URL, "COSING_Annex.II_v2.csv")
        annex3_text = await fetch_or_read_cached(client, ANNEX_III_URL, "COSING_Annex.III_v2.csv")

    prohibited = parse_annex_ii(annex2_text)
    restricted = parse_annex_iii(annex3_text)

    async with session_factory() as db:
        seed_count = await load_seed_data(db)
        cosing_count = await import_cosing_inventory(db, inv_text, prohibited, restricted)

    logger.info(
        "CosIng import finished. Total CosIng: %d, Curated seed: %d",
        cosing_count,
        seed_count,
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
