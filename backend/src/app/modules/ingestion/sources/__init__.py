from app.modules.ingestion.sources.base import (
    RawRecord,
    SourceAdapter,
    compute_content_hash,
)
from app.modules.ingestion.sources.obf import (
    OBFSourceAdapter,
    store_raw_product,
)
from app.modules.ingestion.sources.scraper import (
    GenericScraperAdapter,
    SiteConfig,
    SiteSelectors,
    load_site_config,
    parse_sitemap_xml,
)

__all__ = [
    "GenericScraperAdapter",
    "OBFSourceAdapter",
    "RawRecord",
    "SiteConfig",
    "SiteSelectors",
    "SourceAdapter",
    "compute_content_hash",
    "load_site_config",
    "parse_sitemap_xml",
    "store_raw_product",
]
