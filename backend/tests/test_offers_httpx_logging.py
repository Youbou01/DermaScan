"""The SerpApi request URL contains the API key, so httpx must not log it at INFO."""

import logging

import app.modules.offers.serpapi  # noqa: F401


def test_httpx_logger_does_not_log_info() -> None:
    assert logging.getLogger("httpx").level == logging.WARNING
