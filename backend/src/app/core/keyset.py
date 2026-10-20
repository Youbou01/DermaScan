"""Reusable keyset (cursor) pagination.

Why keyset and not OFFSET: pages stay stable when rows are inserted, and every page costs
the same (index seek), however deep the user scrolls.

Rules for callers:
- The sort column must be NOT NULL in the query (add `WHERE score IS NOT NULL` for scores).
- Order is always (sort column, id) in the SAME direction, so the order is total and a
  matching composite index can serve it.
- The cursor is opaque to the client; its `sort` tag prevents reusing a cursor from another
  ordering.
"""

import base64
import json
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, cast

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, literal, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.errors import UnprocessableError

DEFAULT_LIMIT = 20
MAX_LIMIT = 50

LimitQuery = Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Page size.")]
CursorQuery = Annotated[
    str | None, Query(description="Opaque `next_cursor` from the previous page.")
]


class InvalidCursorError(UnprocessableError):
    code = "invalid-cursor"
    title = "Invalid pagination cursor"


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = Field(
        description="Pass it as `cursor` to get the next page. Null on the last page."
    )


def encode_cursor(sort: str, value: int | float | str | datetime, row_id: uuid.UUID) -> str:
    v = value.isoformat() if isinstance(value, datetime) else value
    raw = json.dumps({"s": sort, "v": v, "id": str(row_id)}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(
    cursor: str, sort: str, parse_value: Callable[[Any], Any]
) -> tuple[Any, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        if data["s"] != sort:
            raise ValueError("cursor belongs to another ordering")
        return parse_value(data["v"]), uuid.UUID(data["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidCursorError from exc


async def paginate[T](
    session: AsyncSession,
    stmt: Select[T],
    *,
    sort: str,
    sort_column: InstrumentedAttribute[Any],
    id_column: InstrumentedAttribute[uuid.UUID],
    key: Callable[[T], tuple[Any, uuid.UUID]],
    parse_value: Callable[[Any], Any],
    limit: int,
    cursor: str | None,
    descending: bool = True,
) -> tuple[list[T], str | None]:
    """Return (items, next_cursor). Fetches limit + 1 rows to know if another page exists."""
    if cursor is not None:
        value, row_id = decode_cursor(cursor, sort, parse_value)
        row = tuple_(sort_column, id_column)
        bound = tuple_(literal(value, sort_column.type), literal(row_id, id_column.type))
        stmt = stmt.where(row < bound if descending else row > bound)

    if descending:
        stmt = stmt.order_by(sort_column.desc(), id_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc(), id_column.asc())

    rows = (await session.scalars(stmt.limit(limit + 1))).all()
    items = cast("list[T]", list(rows))
    next_cursor = None
    if len(items) > limit:
        items = items[:limit]
        next_cursor = encode_cursor(sort, *key(items[-1]))
    return items, next_cursor
