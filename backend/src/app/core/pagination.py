"""Opaque keyset cursors. D7 can extend this with shared query helpers / indexes."""

from __future__ import annotations

import base64
import json
from typing import Any


def encode_cursor(payload: dict[str, Any]) -> str:
    """URL-safe base64 of a small JSON object. Opaque to API clients."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token: str) -> dict[str, Any]:
    """Decode a cursor produced by `encode_cursor`. Raises ValueError if tampered/malformed."""
    if not token or not token.isascii():
        msg = "Cursor is empty or not ASCII."
        raise ValueError(msg)
    padding = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(token + padding)
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        msg = "Cursor is not valid base64 JSON."
        raise ValueError(msg) from exc
    if not isinstance(data, dict):
        msg = "Cursor payload must be an object."
        raise ValueError(msg)
    return data
