"""Request context middleware (pure ASGI, so it does not buffer or break streaming).

For every HTTP request it:
  1. takes the caller's `X-Request-ID` if it looks sane, otherwise generates one,
  2. binds it to the logging context, so every log line of that request carries it,
  3. echoes it back in the response header (the mobile app can show it in bug reports),
  4. writes one access-log line with method, path, status and duration.
"""

import re
import time
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
# Reject anything odd (log injection, huge values): letters, digits, dot, dash, underscore.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

logger = structlog.get_logger("app.access")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER, "")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else str(uuid.uuid7())
        # Also kept on the scope: error handlers that run outside this middleware read it.
        scope.setdefault("state", {})["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        status_code = 500  # what the client gets if the app crashes before responding

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            path: str = scope["path"]
            log = logger.debug if path.startswith("/health") else logger.info  # probes are noisy
            log(
                "request_completed",
                method=scope["method"],
                path=path,
                status_code=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            structlog.contextvars.clear_contextvars()
