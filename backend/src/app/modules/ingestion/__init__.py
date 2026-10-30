"""ingestion module: source adapters (Open Beauty Facts first), staging, seed loaders.

Owns no tables in sprint 1. Writes products only through the catalog public interface.
"""

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
    OBFSourceAdapter,
    RawRecord,
    SourceAdapter,
    compute_content_hash,
    store_raw_product,
)

__all__ = [
    "ImportReport",
    "IngestionRunOut",
    "IngestionService",
    "MappedProduct",
    "OBFAsyncFallbackClient",
    "OBFSourceAdapter",
    "QuarantineItemOut",
    "QuarantineStatus",
    "RawProductOut",
    "RawProductSource",
    "RawRecord",
    "SourceAdapter",
    "compute_content_hash",
    "fetch_remote_product_by_barcode",
    "handle_barcode_miss_fallback",
    "import_product_record",
    "load_category_seed",
    "map_obf_record",
    "resolve_category_slug",
    "seed_categories",
    "store_raw_product",
]
