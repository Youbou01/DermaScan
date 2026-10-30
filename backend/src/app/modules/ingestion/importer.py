"""Robust, clean Open Beauty Facts product importer using public module services."""

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, CreateProductInput
from app.modules.catalog.enums import ProductSource
from app.modules.ingestion.mapper import map_obf_record
from app.modules.ingredients import (
    IngredientService,
    looks_like_ingredient_list,
    parse_ingredient_label,
)

logger = structlog.get_logger(__name__)


@dataclass
class ImportReport:
    fetched: int = 0
    mapped: int = 0
    imported: int = 0
    quarantined: int = 0
    skipped_by_reason: dict[str, int] = field(default_factory=dict)

    def record_skip(self, reason: str) -> None:
        self.skipped_by_reason[reason] = self.skipped_by_reason.get(reason, 0) + 1


async def import_product_record(
    db: AsyncSession,
    row: dict[str, Any],
    ingredient_service: IngredientService | None = None,
    catalog_service: CatalogService | None = None,
    report: ImportReport | None = None,
) -> bool:
    """Import a single raw OBF product record strictly via catalog and ingredients services."""
    if report is None:
        report = ImportReport()
    report.fetched += 1

    mapped = map_obf_record(row)
    report.mapped += 1

    if not mapped.barcode:
        report.record_skip("missing_barcode")
        logger.warning("obf_record_missing_barcode", record_id=row.get("id"))
        return False

    if not mapped.name:
        report.record_skip("missing_name")
        logger.warning("obf_record_missing_name", barcode=mapped.barcode)
        return False

    if not mapped.raw_ingredients_text:
        report.record_skip("missing_ingredients")
        logger.warning("obf_record_missing_ingredients", barcode=mapped.barcode)
        return False

    parsed_items = parse_ingredient_label(
        mapped.raw_ingredients_text, preferred_lang=mapped.source_lang
    )
    if not parsed_items:
        report.record_skip("no_ingredients_parsed")
        logger.warning("obf_record_no_ingredients_parsed", barcode=mapped.barcode)
        return False

    suspicion = looks_like_ingredient_list(parsed_items)
    if suspicion.is_suspicious:
        critical_reasons = {
            "contains_marketing_or_instruction_sentences",
            "excessive_digits",
            "item_exceeds_120_chars",
        }
        if any(r in critical_reasons for r in suspicion.reasons):
            report.quarantined += 1
            report.record_skip("quarantined_suspicious")
            logger.warning(
                "obf_record_quarantined",
                barcode=mapped.barcode,
                reasons=suspicion.reasons,
            )
            return False

    if ingredient_service is None:
        ingredient_service = IngredientService(db)
    if catalog_service is None:
        catalog_service = CatalogService(db)

    raw_tokens = [item.text for item in parsed_items]
    matches = await ingredient_service.match(raw_tokens)

    ingredients_data: list[tuple[int, str, uuid.UUID | None]] = []
    for item, match in zip(parsed_items, matches, strict=True):
        ingredients_data.append((item.position, item.text, match.ingredient_id))

    input_data = CreateProductInput(
        barcode=mapped.barcode,
        name=mapped.name,
        source=ProductSource.OPEN_BEAUTY_FACTS,
        source_id=str(row.get("code") or row.get("id") or mapped.barcode),
        brand_name=mapped.primary_brand,
        category_slug=mapped.category_slug,
        image_url=mapped.image_url,
        raw_ingredients_text=mapped.raw_ingredients_text,
        source_lang=mapped.source_lang,
        name_i18n=mapped.name_i18n,
        field_provenance=mapped.field_provenance,
        ingredients=ingredients_data,
    )

    await catalog_service.upsert_product_from_import(input_data)
    report.imported += 1
    return True
