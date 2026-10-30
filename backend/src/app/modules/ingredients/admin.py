from typing import Any, ClassVar

from sqladmin import ModelView

from app.modules.ingredients.models import Ingredient


class IngredientAdmin(ModelView, model=Ingredient):
    name = "Ingredient"
    name_plural = "Ingredients"
    icon = "fa-solid fa-flask"
    column_list: ClassVar[list[Any]] = [
        Ingredient.id,
        Ingredient.inci_name,
        Ingredient.rating,
        Ingredient.risk_level,
        Ingredient.rating_source,
        Ingredient.is_prohibited,
        Ingredient.is_restricted,
    ]
    column_searchable_list: ClassVar[list[Any]] = [Ingredient.inci_name]
    column_sortable_list: ClassVar[list[Any]] = [Ingredient.inci_name, Ingredient.rating]
