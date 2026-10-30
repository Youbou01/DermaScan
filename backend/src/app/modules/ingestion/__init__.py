"""ingestion module: source adapters (Open Beauty Facts first), staging, seed loaders.

Owns no tables in sprint 1. Writes products only through the catalog public interface.
"""

from app.modules.ingestion.fallback import (
    OBFAsyncFallbackClient,
    fetch_remote_product_by_barcode,
    handle_barcode_miss_fallback,
)
from app.modules.ingestion.importer import ImportReport, import_product_record
from app.modules.ingestion.mapper import MappedProduct, map_obf_record, resolve_category_slug
from app.modules.ingestion.seed_categories import load_category_seed, seed_categories

__all__ = [
    "ImportReport",
    "MappedProduct",
    "OBFAsyncFallbackClient",
    "fetch_remote_product_by_barcode",
    "handle_barcode_miss_fallback",
    "import_product_record",
    "load_category_seed",
    "map_obf_record",
    "resolve_category_slug",
    "seed_categories",
]
