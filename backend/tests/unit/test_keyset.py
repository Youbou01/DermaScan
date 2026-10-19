import base64
import uuid
from datetime import UTC, datetime

import pytest

from app.core.keyset import InvalidCursorError, decode_cursor, encode_cursor

ID = uuid.uuid7()


def test_int_roundtrip() -> None:
    cursor = encode_cursor("score", 87, ID)
    assert decode_cursor(cursor, "score", int) == (87, ID)


def test_datetime_roundtrip() -> None:
    ts = datetime(2026, 10, 19, 12, 30, tzinfo=UTC)
    cursor = encode_cursor("created_at", ts, ID)
    assert decode_cursor(cursor, "created_at", datetime.fromisoformat) == (ts, ID)


def test_cursor_is_url_safe() -> None:
    assert not set("+/=") & set(encode_cursor("score", 1, ID))


@pytest.mark.parametrize("garbage", ["", "abc", "!!!", base64.urlsafe_b64encode(b"[1]").decode()])
def test_garbage_is_rejected(garbage: str) -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor(garbage, "score", int)


def test_cursor_from_another_ordering_is_rejected() -> None:
    cursor = encode_cursor("created_at", datetime.now(UTC), ID)
    with pytest.raises(InvalidCursorError):
        decode_cursor(cursor, "score", int)


def test_bad_value_type_is_rejected() -> None:
    cursor = encode_cursor("score", "not-a-number", ID)
    with pytest.raises(InvalidCursorError):
        decode_cursor(cursor, "score", int)
