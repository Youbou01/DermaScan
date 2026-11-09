"""Application service for routine editing, conflict checks, and recommendations."""

import uuid
from collections.abc import Iterable
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import CatalogService, RoutineProductData
from app.modules.routines.conflict_engine import (
    ProductActiveProfile,
    detect_routine_conflicts,
    extract_actives,
)
from app.modules.routines.enums import RoutineSlot, RoutineStepType
from app.modules.routines.exceptions import (
    InvalidRoutineStepsError,
    RoutineNotFoundError,
    RoutineProductNotFoundError,
)
from app.modules.routines.models import Routine
from app.modules.routines.repository import RoutineRepository
from app.modules.routines.schemas import (
    ConflictCheckOut,
    RecommendedRoutinesOut,
    RoutineDataOut,
    RoutineStepIn,
    RoutineStepOut,
)

_DRY_OR_SENSITIVE_AVOIDED_INCI = frozenset({"ALCOHOL DENAT.", "SODIUM LAURYL SULFATE"})
_OILY_AVOIDED_INCI = frozenset({"COCONUT OIL", "ISOPROPYL MYRISTATE"})


class RoutineService:
    """Coordinates routine-owned persistence with catalog's public projections."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = RoutineRepository(session)
        self._catalog = CatalogService(session)

    async def list_routines(self, user_id: uuid.UUID, locale: str) -> list[RoutineDataOut]:
        routines = await self._repository.list_for_user(user_id)
        completed_ids = await self._repository.completed_routine_ids(
            [routine.id for routine in routines], _today()
        )
        return [
            await self._to_out(routine, locale, routine.id in completed_ids) for routine in routines
        ]

    async def replace_routine(
        self,
        user_id: uuid.UUID,
        slot: RoutineSlot,
        steps: list[RoutineStepIn],
        locale: str,
    ) -> RoutineDataOut:
        self._validate_steps(steps)
        product_map = await self._products_or_raise([step.product_id for step in steps], locale)
        routine = await self._repository.get_or_create_for_user_slot(user_id, slot)
        stored = await self._repository.replace_steps(
            routine,
            [(step.step_order, step.step_type, step.product_id, step.notes) for step in steps],
        )
        # Resolving the products before the replacement gives a validation failure before
        # any write, while this call keeps the response based on freshly loaded data.
        del product_map
        completed_ids = await self._repository.completed_routine_ids([stored.id], _today())
        return await self._to_out(stored, locale, completed_today=stored.id in completed_ids)

    async def check_product_conflict(
        self,
        user_id: uuid.UUID,
        slot: RoutineSlot,
        product_id: uuid.UUID,
        locale: str,
    ) -> ConflictCheckOut:
        routine = await self._repository.get_for_user_slot(user_id, slot)
        product_ids = [step.product_id for step in routine.steps] if routine else []
        if product_id not in product_ids:
            product_ids.append(product_id)
        products = await self._products_or_raise(product_ids, locale)
        conflicts = detect_routine_conflicts(_active_profiles(products.values()), locale)
        return ConflictCheckOut(has_conflict=bool(conflicts), conflicts=conflicts)

    async def toggle_completion(
        self, user_id: uuid.UUID, slot: RoutineSlot, locale: str
    ) -> RoutineDataOut:
        routine = await self._repository.get_for_user_slot(user_id, slot)
        if routine is None:
            raise RoutineNotFoundError(f"No {slot.value} routine exists for this user.")
        completed = await self._repository.toggle_completion(routine.id, _today())
        return await self._to_out(routine, locale, completed_today=completed)

    async def recommendations(self, skin_type: str, locale: str) -> RecommendedRoutinesOut:
        """Build deterministic, skin-type-aware, conflict-free AM and PM sequences."""
        candidates = await self._catalog.get_routine_recommendation_candidates(
            skin_type=skin_type,
            locale=locale,
        )
        compatible_candidates = [
            candidate
            for candidate in candidates
            if _is_compatible_with_skin_type(candidate, skin_type)
        ]
        morning = _recommendation_steps(
            compatible_candidates,
            (
                (RoutineStepType.CLEANSER, ("cleanser",)),
                (RoutineStepType.SERUM, ("serum",)),
                (RoutineStepType.MOISTURIZER, ("moisturizer",)),
                (RoutineStepType.SUNSCREEN, ("sunscreen",)),
            ),
            locale,
        )
        evening = _recommendation_steps(
            compatible_candidates,
            (
                (RoutineStepType.CLEANSER, ("cleanser",)),
                (RoutineStepType.TREATMENT, ("treatment", "serum")),
                (RoutineStepType.MOISTURIZER, ("moisturizer",)),
            ),
            locale,
        )
        return RecommendedRoutinesOut(skin_type=skin_type, morning=morning, evening=evening)

    async def _to_out(self, routine: Routine, locale: str, completed_today: bool) -> RoutineDataOut:
        product_map = await self._products_or_raise(
            [step.product_id for step in routine.steps], locale
        )
        ordered_products = [product_map[step.product_id] for step in routine.steps]
        return RoutineDataOut(
            id=routine.id,
            slot=routine.slot,
            name=routine.name,
            completed_today=completed_today,
            steps=[
                RoutineStepOut(
                    id=step.id,
                    step_order=step.step_order,
                    step_type=step.step_type,
                    product=product_map[step.product_id].product,
                    active_ingredients=extract_actives(
                        list(product_map[step.product_id].ingredient_inci_names),
                        product_map[step.product_id].category_slug,
                    ),
                    notes=step.notes,
                )
                for step in routine.steps
            ],
            conflicts=detect_routine_conflicts(_active_profiles(ordered_products), locale),
        )

    async def _products_or_raise(
        self, product_ids: list[uuid.UUID], locale: str
    ) -> dict[uuid.UUID, RoutineProductData]:
        products = await self._catalog.get_products_for_routine(product_ids, locale)
        missing = set(product_ids) - products.keys()
        if missing:
            raise RoutineProductNotFoundError(f"Product {next(iter(missing))} does not exist.")
        return products

    @staticmethod
    def _validate_steps(steps: list[RoutineStepIn]) -> None:
        orders = [step.step_order for step in steps]
        product_ids = [step.product_id for step in steps]
        if len(orders) != len(set(orders)):
            raise InvalidRoutineStepsError("Each routine step must have a distinct step_order.")
        if orders != list(range(1, len(steps) + 1)):
            raise InvalidRoutineStepsError(
                "Routine steps must use consecutive 1-based step_order values."
            )
        if len(product_ids) != len(set(product_ids)):
            raise InvalidRoutineStepsError("A product can appear only once in the same routine.")


def _active_profiles(products: Iterable[RoutineProductData]) -> list[ProductActiveProfile]:
    return [
        ProductActiveProfile(
            product_id=item.product.id,
            product_name=item.product.name,
            active_ingredients=item.ingredient_inci_names,
            category_slug=item.category_slug,
        )
        for item in products
    ]


def _recommendation_steps(
    candidates: list[RoutineProductData],
    plan: tuple[tuple[RoutineStepType, tuple[str, ...]], ...],
    locale: str,
) -> list[RoutineStepOut]:
    selected: list[RoutineProductData] = []
    steps: list[RoutineStepOut] = []
    used_ids: set[uuid.UUID] = set()
    for step_type, category_slugs in plan:
        matching = (
            candidate
            for candidate in candidates
            if candidate.category_slug in category_slugs and candidate.product.id not in used_ids
        )
        candidate = next(
            (
                item
                for item in matching
                if not detect_routine_conflicts(_active_profiles([*selected, item]), locale)
            ),
            None,
        )
        if candidate is None:
            continue
        selected.append(candidate)
        used_ids.add(candidate.product.id)
        steps.append(
            RoutineStepOut(
                step_order=len(steps) + 1,
                step_type=step_type,
                product=candidate.product,
                active_ingredients=extract_actives(
                    list(candidate.ingredient_inci_names), candidate.category_slug
                ),
            )
        )
    return steps


def _is_compatible_with_skin_type(candidate: RoutineProductData, skin_type: str) -> bool:
    """Keep recommendations deterministic without reaching into identity persistence.

    The routine API accepts an explicit skin-type value, so this remains usable before
    profile retrieval is added to identity's public service boundary.
    """
    ingredient_names = {name.upper() for name in candidate.ingredient_inci_names}
    normalized_skin_type = skin_type.lower()
    if normalized_skin_type in {"dry", "sensitive"}:
        return not bool(ingredient_names & _DRY_OR_SENSITIVE_AVOIDED_INCI)
    if normalized_skin_type == "oily":
        return not bool(ingredient_names & _OILY_AVOIDED_INCI)
    return True


def _today() -> date:
    return datetime.now(UTC).date()
