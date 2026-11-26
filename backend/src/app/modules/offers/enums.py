"""Offer-owned vocabulary persisted as checked VARCHAR columns."""

from enum import StrEnum


class StockState(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"
