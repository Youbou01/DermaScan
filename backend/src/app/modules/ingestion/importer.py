import uuid
from typing import Any, cast

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.catalog.enums import ProductSource
from app.modules.catalog.gtin import normalize_gtin
from app.modules.catalog.search_text import normalize_name
from app.modules.ingestion.mapper import resolve_category_slug
from app.modules.ingredients.parser import parse_ingredient_label
from app.modules.ingredients.service import IngredientService
from app.modules.scoring import (
    IngredientPositionInput,
    calculate_score,
)

logger = structlog.get_logger()


async def get_or_create_brand_id(db: AsyncSession, brand_name: str) -> uuid.UUID | None:
    if not brand_name:
        return None
    clean_name = brand_name.split(",")[0].strip()
    if not clean_name:
        return None

    res = await db.execute(
        text("SELECT id FROM brand WHERE lower(name) = lower(:name)").bindparams(name=clean_name)
    )
    row = res.fetchone()
    if row:
        return cast(uuid.UUID, row[0])

    new_id = uuid.uuid4()
    ins = await db.execute(
        text("INSERT INTO brand (id, name) VALUES (:id, :name) RETURNING id").bindparams(
            id=new_id, name=clean_name
        )
    )
    brand_id = cast(uuid.UUID, ins.scalar_one())
    await db.flush()
    return brand_id


async def get_category_id_by_slug(db: AsyncSession, slug: str) -> uuid.UUID | None:
    res = await db.execute(text("SELECT id FROM category WHERE slug = :slug").bindparams(slug=slug))
    row = res.fetchone()
    return cast(uuid.UUID, row[0]) if row else None


async def import_product_record(
    db: AsyncSession, row: dict[str, Any], ingredient_service: IngredientService
) -> bool:
    code = str(row.get("code") or "").strip()
    name = str(row.get("product_name") or "").strip()
    ing_text = str(row.get("ingredients_text") or "").strip()
    brand_name = str(row.get("brands") or "").strip()
    image_url = str(row.get("image_url") or "").strip()
    cat_tags = row.get("categories_tags") or []

    if not code or not name or not ing_text:
        return False

    try:
        gtin13_barcode = normalize_gtin(code)
    except Exception:
        return False

    source_id = code
    parsed_items = parse_ingredient_label(ing_text)
    raw_tokens = [item.text for item in parsed_items]

    if not raw_tokens:
        return False

    matches = await ingredient_service.match(raw_tokens)

    scoring_inputs: list[IngredientPositionInput] = []
    matched_ingredients_data: list[dict[str, Any]] = []

    matched_ids = [m.ingredient_id for m in matches if m and m.ingredient_id]
    ingredient_map = {}
    if matched_ids:
        ingredient_map = await ingredient_service.get_many(matched_ids, locale="en")

    for idx, (parsed_item, match_result) in enumerate(
        zip(parsed_items, matches, strict=False), start=1
    ):
        risk = RiskLevel.UNKNOWN
        ing_id = match_result.ingredient_id if match_result else None

        if ing_id and ing_id in ingredient_map:
            ing_info = ingredient_map[ing_id]
            if ing_info.risk_level:
                risk_val = str(ing_info.risk_level).lower()
                if risk_val in {"low", "moderate", "high", "unknown"}:
                    risk = RiskLevel(risk_val)

        scoring_inputs.append(IngredientPositionInput(risk_level=risk, position=idx))
        matched_ingredients_data.append(
            {
                "position": idx,
                "raw_text": parsed_item.text,
                "ingredient_id": ing_id,
            }
        )

    score_output = calculate_score(scoring_inputs)

    brand_id = await get_or_create_brand_id(db, brand_name)
    cat_slug = resolve_category_slug(list(cat_tags) if isinstance(cat_tags, list) else [])
    category_id = await get_category_id_by_slug(db, cat_slug)

    res = await db.execute(
        text("SELECT id FROM product WHERE source = :source AND source_id = :source_id").bindparams(
            source=ProductSource.OPEN_BEAUTY_FACTS.value, source_id=source_id
        )
    )
    prod_row = res.fetchone()

    score_val = score_output.score
    score_band_val = score_output.band.value
    coverage_val = score_output.coverage
    version_val = score_output.scoring_version

    if not prod_row:
        new_prod_id = uuid.uuid4()
        ins_prod = await db.execute(
            text(
                """
                INSERT INTO product (
                    id, barcode, name, name_normalized, brand_id, primary_category_id,
                    image_url, raw_ingredients_text, source, source_id,
                    score, score_band, score_coverage, scoring_version
                )
                VALUES (
                    :id, :barcode, :name, :name_normalized, :brand_id, :primary_category_id,
                    :image_url, :raw_ingredients_text, :source, :source_id,
                    :score, :score_band, :score_coverage, :scoring_version
                )
                RETURNING id
                """
            ).bindparams(
                id=new_prod_id,
                barcode=gtin13_barcode,
                name=name,
                name_normalized=normalize_name(name),
                brand_id=brand_id,
                primary_category_id=category_id,
                image_url=image_url if image_url else None,
                raw_ingredients_text=ing_text,
                source=ProductSource.OPEN_BEAUTY_FACTS.value,
                source_id=source_id,
                score=score_val,
                score_band=score_band_val,
                score_coverage=coverage_val,
                scoring_version=version_val,
            )
        )
        product_id = cast(uuid.UUID, ins_prod.scalar_one())
        await db.flush()
    else:
        product_id = cast(uuid.UUID, prod_row[0])
        await db.execute(
            text(
                """
                UPDATE product
                SET barcode = :barcode, name = :name, name_normalized = :name_normalized,
                    brand_id = :brand_id,
                    primary_category_id = :primary_category_id,
                    image_url = :image_url, raw_ingredients_text = :raw_ingredients_text,
                    score = :score, score_band = :score_band,
                    score_coverage = :score_coverage, scoring_version = :scoring_version
                WHERE id = :id
                """
            ).bindparams(
                id=product_id,
                barcode=gtin13_barcode,
                name=name,
                name_normalized=normalize_name(name),
                brand_id=brand_id,
                primary_category_id=category_id,
                image_url=image_url if image_url else None,
                raw_ingredients_text=ing_text,
                score=score_val,
                score_band=score_band_val,
                score_coverage=coverage_val,
                scoring_version=version_val,
            )
        )
        await db.execute(
            text("DELETE FROM product_ingredient WHERE product_id = :pid").bindparams(
                pid=product_id
            )
        )
        await db.flush()

    for item_data in matched_ingredients_data:
        await db.execute(
            text(
                """
                INSERT INTO product_ingredient (product_id, position, raw_text, ingredient_id)
                VALUES (:product_id, :position, :raw_text, :ingredient_id)
                """
            ).bindparams(
                product_id=product_id,
                position=item_data["position"],
                raw_text=item_data["raw_text"],
                ingredient_id=item_data["ingredient_id"],
            )
        )

    return True
