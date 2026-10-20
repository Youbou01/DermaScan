"""catalog module: products, brands, categories, search and the home feed.

Owns tables: product, brand, category, category_translation, product_ingredient.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from here,
never from `models` or `repository` (enforced by import-linter).
"""

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
<<<<<<< HEAD
    CategoryGridSectionOut,
=======
>>>>>>> 1fd479cb87dbe5bed5fa5de16d93293b1e777d0e
    CategoryNodeOut,
    CategoryOut,
    HomeFeedOut,
    HomeSectionOut,
    ProductCardOut,
    ProductDetail,
    ProductIngredientOut,
    ProductShelfSectionOut,
)
from app.modules.catalog.service import CatalogService

__all__ = [
    "CatalogService",
<<<<<<< HEAD
    "CategoryGridSectionOut",
=======
>>>>>>> 1fd479cb87dbe5bed5fa5de16d93293b1e777d0e
    "CategoryNodeOut",
    "CategoryOut",
    "CategorySeedNode",
    "CategoryService",
    "HomeFeedOut",
    "HomeFeedService",
    "HomeSectionOut",
    "InvalidBarcodeError",
    "InvalidCursorError",
    "InvalidLimitError",
    "ProductCardOut",
    "ProductDetail",
    "ProductIngredientOut",
    "ProductNotFoundError",
<<<<<<< HEAD
    "ProductShelfSectionOut",
=======
>>>>>>> 1fd479cb87dbe5bed5fa5de16d93293b1e777d0e
    "SectionNotFoundError",
    "catalog_router",
    "categories_router",
    "home_router",
    "normalize_gtin",
]
