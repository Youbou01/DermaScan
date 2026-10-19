"""Shared helpers for integration tests (keep factories in tests/factories.py)."""

from datetime import date

import httpx
from fastapi import FastAPI


def app_from_client(client: httpx.AsyncClient) -> FastAPI:
    transport = client._transport
    assert isinstance(transport, httpx.ASGITransport)
    app = transport.app
    assert isinstance(app, FastAPI)
    return app


def freeze_home_feed_date(client: httpx.AsyncClient, day: date) -> None:
    """Pin the Top-rated daily rotation for the lifetime of this test client."""
    app_from_client(client).state.settings.home_feed_date = day
