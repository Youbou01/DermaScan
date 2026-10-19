"""catalog module: products, brands, categories, search and the home feed.

Owns tables: product, brand, category, category_translation, product_ingredient.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from here,
never from `models` or `repository` (enforced by import-linter).
"""

from app.modules.catalog.exceptions import InvalidBarcodeError, ProductNotFoundError
from app.modules.catalog.gtin import normalize_gtin
from app.modules.catalog.router import router as catalog_router
from app.modules.catalog.schemas import (
    CategoryOut,
    ProductDetail,
    ProductIngredientOut,
)
from app.modules.catalog.service import CatalogService

__all__ = [
    "CatalogService",
    "CategoryOut",
    "InvalidBarcodeError",
    "ProductDetail",
    "ProductIngredientOut",
    "ProductNotFoundError",
    "catalog_router",
    "normalize_gtin",
]
