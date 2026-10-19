"""SQL for categories. Private to the catalog module."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import Category, CategoryTranslation


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_with_translations(self) -> list[Category]:
        result = await self._session.scalars(
            select(Category).options(selectinload(Category.translations)).order_by(Category.slug)
        )
        return list(result)

    async def get_by_slug(self, slug: str) -> Category | None:
        return await self._session.scalar(
            select(Category)
            .options(selectinload(Category.translations))
            .where(Category.slug == slug)
        )

    async def add(self, category: Category) -> Category:
        self._session.add(category)
        await self._session.flush()
        return category

    async def upsert_translation(self, category_id: uuid.UUID, locale: str, name: str) -> bool:
        """Insert or update one translation. Returns True when a row was created or changed."""
        existing = await self._session.scalar(
            select(CategoryTranslation).where(
                CategoryTranslation.category_id == category_id,
                CategoryTranslation.locale == locale,
            )
        )
        if existing is None:
            self._session.add(
                CategoryTranslation(category_id=category_id, locale=locale, name=name)
            )
            await self._session.flush()
            return True
        if existing.name != name:
            existing.name = name
            await self._session.flush()
            return True
        return False

    async def set_parent(self, category: Category, parent_id: uuid.UUID | None) -> bool:
        if category.parent_id == parent_id:
            return False
        category.parent_id = parent_id
        await self._session.flush()
        return True
