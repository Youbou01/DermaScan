"""catalog module: products, brands, categories, search and the home feed.

Owns tables: product, brand, category, category_translation, product_ingredient.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from here,
never from `models` or `repository` (enforced by import-linter).
"""

from app.modules.catalog.admin import ProductAdmin
from app.modules.catalog.categories_router import router as categories_router
from app.modules.catalog.category_service import CategorySeedNode, CategoryService
from app.modules.catalog.exceptions import (
    InvalidBarcodeError,
    InvalidCursorError,
    InvalidLimitError,
    ProductNotFoundError,
    SectionNotFoundError,
)
from app.modules.catalog.gtin import normalize_gtin
from app.modules.catalog.home_router import router as home_router
from app.modules.catalog.home_service import HomeFeedService
from app.modules.catalog.router import router as catalog_router
from app.modules.catalog.schemas import (
    CategoryNodeOut,
    CategoryOut,
    CreateProductInput,
    DeduplicationResult,
    HomeFeedOut,
    HomeSectionOut,
    ProductCardOut,
    ProductDetail,
    ProductIngredientOut,
    ProductUpsert,
)
from app.modules.catalog.service import CatalogService
from app.modules.ingredients.service import IngredientService

IngredientService.register_dirty_hook(
    lambda session, ids: CatalogService(session).mark_products_dirty_for_ingredients(ids)
)

__all__ = [
    "CatalogService",
    "CategoryNodeOut",
    "CategoryOut",
    "CategorySeedNode",
    "CategoryService",
    "CreateProductInput",
    "DeduplicationResult",
    "HomeFeedOut",
    "HomeFeedService",
    "HomeSectionOut",
    "InvalidBarcodeError",
    "InvalidCursorError",
    "InvalidLimitError",
    "ProductAdmin",
    "ProductCardOut",
    "ProductDetail",
    "ProductIngredientOut",
    "ProductNotFoundError",
    "ProductUpsert",
    "SectionNotFoundError",
    "catalog_router",
    "categories_router",
    "home_router",
    "normalize_gtin",
]
