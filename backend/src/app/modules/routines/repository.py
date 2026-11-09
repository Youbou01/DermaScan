"""SQL access for routines. Other modules use RoutineService instead."""

import uuid
from datetime import date

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.routines.enums import RoutineSlot
from app.modules.routines.models import Routine, RoutineCompletionLog, RoutineStep


class RoutineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _with_steps() -> Select[Routine]:
        return select(Routine).options(selectinload(Routine.steps))

    async def list_for_user(self, user_id: uuid.UUID) -> list[Routine]:
        statement = (
            self._with_steps()
            .where(Routine.user_id == user_id, Routine.is_active.is_(True))
            .order_by(Routine.slot)
        )
        return list((await self._session.scalars(statement)).unique().all())

    async def get_for_user_slot(self, user_id: uuid.UUID, slot: RoutineSlot) -> Routine | None:
        statement = self._with_steps().where(Routine.user_id == user_id, Routine.slot == slot)
        return (await self._session.scalars(statement)).unique().one_or_none()

    async def get_or_create_for_user_slot(self, user_id: uuid.UUID, slot: RoutineSlot) -> Routine:
        existing = await self.get_for_user_slot(user_id, slot)
        if existing is not None:
            return existing
        routine = Routine(user_id=user_id, slot=slot, name=_default_name(slot), is_active=True)
        self._session.add(routine)
        await self._session.flush()
        return routine

    async def replace_steps(
        self,
        routine: Routine,
        steps: list[tuple[int, str, uuid.UUID, str | None]],
    ) -> Routine:
        await self._session.execute(delete(RoutineStep).where(RoutineStep.routine_id == routine.id))
        self._session.add_all(
            [
                RoutineStep(
                    routine_id=routine.id,
                    step_order=step_order,
                    step_type=step_type,
                    product_id=product_id,
                    notes=notes,
                )
                for step_order, step_type, product_id, notes in steps
            ]
        )
        await self._session.flush()
        refreshed = await self.get_for_user_slot(routine.user_id, routine.slot)
        if refreshed is None:  # defensive: a routine cannot disappear within this transaction
            raise RuntimeError("Routine disappeared while replacing its steps")
        return refreshed

    async def completed_routine_ids(
        self, routine_ids: list[uuid.UUID], day: date
    ) -> set[uuid.UUID]:
        if not routine_ids:
            return set()
        statement = select(RoutineCompletionLog.routine_id).where(
            RoutineCompletionLog.routine_id.in_(routine_ids),
            RoutineCompletionLog.completed_date == day,
        )
        return set((await self._session.scalars(statement)).all())

    async def toggle_completion(self, routine_id: uuid.UUID, day: date) -> bool:
        existing = await self._session.scalar(
            select(RoutineCompletionLog).where(
                RoutineCompletionLog.routine_id == routine_id,
                RoutineCompletionLog.completed_date == day,
            )
        )
        if existing is not None:
            await self._session.delete(existing)
            await self._session.flush()
            return False
        self._session.add(RoutineCompletionLog(routine_id=routine_id, completed_date=day))
        await self._session.flush()
        return True


def _default_name(slot: RoutineSlot) -> str:
    return "Morning Routine" if slot == RoutineSlot.MORNING else "Evening Routine"
