from typing import Any, ClassVar

from sqladmin import ModelView

from app.modules.catalog.models import Product


class ProductAdmin(ModelView, model=Product):
    name = "Product"
    name_plural = "Products"
    icon = "fa-solid fa-bottle-droplet"
    column_list: ClassVar[list[Any]] = [
        Product.id,
        Product.barcode,
        Product.name,
        Product.score,
        Product.score_band,
        Product.enrichment_status,
        Product.image_status,
        Product.score_dirty,
    ]
    column_searchable_list: ClassVar[list[Any]] = [Product.barcode, Product.name]
    column_sortable_list: ClassVar[list[Any]] = [Product.name, Product.score, Product.created_at]
