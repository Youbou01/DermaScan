import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.core.config import Settings, get_settings


def verify_admin_key(
    request: Request,
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> str:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    configured_key = settings.admin_api_key or "test-admin-key"

    if not x_admin_key or not secrets.compare_digest(x_admin_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Key",
        )
    return x_admin_key


class AdminAuth(AuthenticationBackend):
    def __init__(
        self,
        secret_key: str,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        super().__init__(secret_key=secret_key)
        self.ui_user = user or "admin"
        self.ui_password = password or "admin"

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            return False

        if secrets.compare_digest(str(username), self.ui_user) and secrets.compare_digest(
            str(password), self.ui_password
        ):
            request.session.update({"admin_user": self.ui_user})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return "admin_user" in request.session
