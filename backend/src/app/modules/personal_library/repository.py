"""SQL access for saved and recently viewed products."""

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.keyset import paginate
from app.modules.personal_library.models import RecentlyViewedProduct, SavedProduct

MAX_RECENTLY_VIEWED = 20


class PersonalLibraryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._session.execute(
            insert(SavedProduct)
            .values(user_id=user_id, product_id=product_id)
            .on_conflict_do_nothing(index_elements=["user_id", "product_id"])
        )

    async def unsave_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(SavedProduct).where(
                SavedProduct.user_id == user_id, SavedProduct.product_id == product_id
            )
        )

    async def is_saved(self, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        return (
            await self._session.scalar(
                select(SavedProduct.product_id).where(
                    SavedProduct.user_id == user_id,
                    SavedProduct.product_id == product_id,
                )
            )
            is not None
        )

    async def list_saved_products(
        self, user_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[SavedProduct], str | None]:
        statement = select(SavedProduct).where(SavedProduct.user_id == user_id)
        return await paginate(
            self._session,
            statement,
            sort="saved_at_desc",
            sort_column=SavedProduct.saved_at,
            id_column=SavedProduct.product_id,
            key=lambda row: (row.saved_at, row.product_id),
            parse_value=datetime.fromisoformat,
            limit=limit,
            cursor=cursor,
        )

    async def record_view(self, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        await self._session.execute(
            insert(RecentlyViewedProduct)
            .values(user_id=user_id, product_id=product_id, viewed_at=func.now())
            .on_conflict_do_update(
                index_elements=["user_id", "product_id"], set_={"viewed_at": func.now()}
            )
        )
        ranked = (
            select(
                RecentlyViewedProduct.product_id,
                func.row_number()
                .over(
                    order_by=(
                        RecentlyViewedProduct.viewed_at.desc(),
                        RecentlyViewedProduct.product_id.desc(),
                    )
                )
                .label("rank"),
            )
            .where(RecentlyViewedProduct.user_id == user_id)
            .subquery()
        )
        await self._session.execute(
            delete(RecentlyViewedProduct).where(
                RecentlyViewedProduct.user_id == user_id,
                RecentlyViewedProduct.product_id.in_(
                    select(ranked.c.product_id).where(ranked.c.rank > MAX_RECENTLY_VIEWED)
                ),
            )
        )

    async def list_recently_viewed(
        self, user_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[RecentlyViewedProduct], str | None]:
        statement = select(RecentlyViewedProduct).where(RecentlyViewedProduct.user_id == user_id)
        return await paginate(
            self._session,
            statement,
            sort="viewed_at_desc",
            sort_column=RecentlyViewedProduct.viewed_at,
            id_column=RecentlyViewedProduct.product_id,
            key=lambda row: (row.viewed_at, row.product_id),
            parse_value=datetime.fromisoformat,
            limit=limit,
            cursor=cursor,
        )
