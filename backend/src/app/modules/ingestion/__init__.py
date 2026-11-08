"""ingestion module: source adapters (Open Beauty Facts first), staging, seed loaders.

Owns no tables in sprint 1. Writes products only through the catalog public interface.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrichment import register_divergence_hook
from app.modules.ingestion.admin import (
    IngestionRunAdmin,
    QuarantineItemAdmin,
    RawProductAdmin,
)
from app.modules.ingestion.enums import QuarantineStatus, RawProductSource
from app.modules.ingestion.fallback import (
    OBFAsyncFallbackClient,
    fetch_remote_product_by_barcode,
    handle_barcode_miss_fallback,
)
from app.modules.ingestion.importer import ImportReport, import_product_record
from app.modules.ingestion.mapper import MappedProduct, map_obf_record, resolve_category_slug
from app.modules.ingestion.schemas import (
    IngestionRunOut,
    QuarantineItemOut,
    RawProductOut,
)
from app.modules.ingestion.seed_categories import load_category_seed, seed_categories
from app.modules.ingestion.service import IngestionService
from app.modules.ingestion.sources import (
    GenericScraperAdapter,
    OBFSourceAdapter,
    RawRecord,
    SiteConfig,
    SiteSelectors,
    SourceAdapter,
    compute_content_hash,
    load_site_config,
    parse_sitemap_xml,
    store_raw_product,
)


async def _quarantine_rating_divergence(session: AsyncSession, payload: dict[str, Any]) -> None:
    svc = IngestionService(session)
    await svc.quarantine(
        raw_product_id=None,
        stage="rating_divergence",
        reason="model_disagreement",
        payload=payload,
    )


register_divergence_hook(_quarantine_rating_divergence)

__all__ = [
    "GenericScraperAdapter",
    "ImportReport",
    "IngestionRunAdmin",
    "IngestionRunOut",
    "IngestionService",
    "MappedProduct",
    "OBFAsyncFallbackClient",
    "OBFSourceAdapter",
    "QuarantineItemAdmin",
    "QuarantineItemOut",
    "QuarantineStatus",
    "RawProductAdmin",
    "RawProductOut",
    "RawProductSource",
    "RawRecord",
    "SiteConfig",
    "SiteSelectors",
    "SourceAdapter",
    "compute_content_hash",
    "fetch_remote_product_by_barcode",
    "handle_barcode_miss_fallback",
    "import_product_record",
    "load_category_seed",
    "load_site_config",
    "map_obf_record",
    "parse_sitemap_xml",
    "resolve_category_slug",
    "seed_categories",
    "store_raw_product",
]
