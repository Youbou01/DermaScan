import pytest

from app.core.pagination import decode_cursor, encode_cursor


def test_encode_decode_round_trip() -> None:
    payload = {"s": "top_rated", "d": "2026-10-19", "score": 90, "rot": "abc", "id": "x"}
    assert decode_cursor(encode_cursor(payload)) == payload


@pytest.mark.parametrize("token", ["", "%%%", "not-base64!!", "null"])
def test_decode_rejects_garbage(token: str) -> None:
    with pytest.raises(ValueError, match=r"(?i)cursor|ascii|base64|object|json"):
        decode_cursor(token)
