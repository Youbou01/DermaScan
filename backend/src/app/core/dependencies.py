"""FastAPI dependencies shared by every module's router.

They live in `core` (not in `app/api`) because module routers need them, and modules are
not allowed to import from the `api` layer above them.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.i18n import resolve_locale


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "session_factory", None
    )
    if factory is None:
        parent_app = request.scope.get("app")
        if parent_app is not None:
            factory = getattr(parent_app.state, "session_factory", None)
    if factory is None:
        raise RuntimeError("No session_factory available in application state")
    async with factory() as session:
        yield session


async def get_locale(request: Request, response: Response) -> str:
    """The response language, from `Accept-Language`, falling back to English."""
    locale = resolve_locale(request.headers.get("accept-language"))
    response.headers["Content-Language"] = locale
    response.headers.append("Vary", "Accept-Language")
    return locale


SessionDep = Annotated[AsyncSession, Depends(get_session)]
LocaleDep = Annotated[str, Depends(get_locale)]
