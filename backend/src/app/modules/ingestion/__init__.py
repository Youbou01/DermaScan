"""ingestion module: source adapters (Open Beauty Facts first), staging, seed loaders.

Owns no tables in sprint 1. Writes products only through the catalog public interface.
"""

from app.modules.ingestion.seed_categories import load_category_seed, seed_categories

__all__ = ["load_category_seed", "seed_categories"]
