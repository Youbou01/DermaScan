"""Routine-owned vocabulary persisted as checked VARCHAR columns."""

from enum import StrEnum


class RoutineSlot(StrEnum):
    MORNING = "morning"
    EVENING = "evening"


class RoutineStepType(StrEnum):
    CLEANSER = "cleanser"
    TONER = "toner"
    SERUM = "serum"
    MOISTURIZER = "moisturizer"
    SUNSCREEN = "sunscreen"
    TREATMENT = "treatment"
