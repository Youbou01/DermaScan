from typing import Any, ClassVar

from sqladmin import ModelView

from app.modules.ingestion.models import IngestionRun, QuarantineItem, RawProduct


class QuarantineItemAdmin(ModelView, model=QuarantineItem):
    name = "Quarantine Item"
    name_plural = "Quarantine Items"
    icon = "fa-solid fa-triangle-exclamation"
    column_list: ClassVar[list[Any]] = [
        QuarantineItem.id,
        QuarantineItem.stage,
        QuarantineItem.reason,
        QuarantineItem.status,
        QuarantineItem.reviewed_by,
        QuarantineItem.created_at,
    ]
    column_sortable_list: ClassVar[list[Any]] = [
        QuarantineItem.created_at,
        QuarantineItem.status,
    ]


class RawProductAdmin(ModelView, model=RawProduct):
    name = "Raw Product"
    name_plural = "Raw Products"
    icon = "fa-solid fa-database"
    column_list: ClassVar[list[Any]] = [
        RawProduct.id,
        RawProduct.source,
        RawProduct.source_id,
        RawProduct.fetched_at,
    ]
    column_searchable_list: ClassVar[list[Any]] = [RawProduct.source_id]


class IngestionRunAdmin(ModelView, model=IngestionRun):
    name = "Ingestion Run"
    name_plural = "Ingestion Runs"
    icon = "fa-solid fa-clock-rotate-left"
    column_list: ClassVar[list[Any]] = [
        IngestionRun.id,
        IngestionRun.source,
        IngestionRun.started_at,
        IngestionRun.finished_at,
    ]
