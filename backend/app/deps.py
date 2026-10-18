from __future__ import annotations

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import Database, get_db
from app.domain.rbac import Principal
from app.errors import AppError
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def db_dep() -> Database:
    return get_db()


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Database = Depends(db_dep),
) -> dict:
    if creds is None or creds.scheme.lower() != "bearer":
        raise AppError("Please sign in to continue", 401, "UNAUTHORIZED")
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise AppError("Your session expired. Please sign in again.", 401, "UNAUTHORIZED") from None
    if payload.get("typ") != "access":
        raise AppError("Invalid access token", 401, "UNAUTHORIZED")
    user = db.col("users").find_one({"_id": payload.get("sub")})
    if not user or not user.get("is_active", True):
        raise AppError("Account is not available", 401, "UNAUTHORIZED")
    return user


def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Database = Depends(db_dep),
) -> dict | None:
    if creds is None:
        return None
    try:
        return current_user(creds, db)
    except AppError:
        return None


def principal_of(user: dict) -> Principal:
    return Principal(id=user["_id"], role=user["role"], department_id=user.get("department_id"))


def require_roles(*roles: str):
    allowed = set(roles)
    if "OFFICER" in allowed:
        allowed.update({"ADMIN_L1", "ADMIN_L2"})
    if "ADMIN" in allowed:
        allowed.update({"ADMIN_L1", "ADMIN_L2", "ADMIN_L3"})

    def _inner(user: dict = Depends(current_user)) -> dict:
        if user.get("role") not in allowed:
            raise AppError("You do not have permission to do that", 403, "FORBIDDEN")
        return user

    return _inner


def require_internal(
    request: Request,
    x_civicon_task: str | None = Header(default=None, alias="X-Civicon-Task"),
    authorization: str | None = Header(default=None),
):
    from app.config import get_settings

    settings = get_settings()
    secret = settings.internal_task_secret
    if not secret:
        raise AppError("INTERNAL_TASK_SECRET is not configured", 503, "TASK_SECRET_MISSING")
    presented = x_civicon_task
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization.split(" ", 1)[1]
    if not presented or presented != secret:
        raise AppError("Internal task authorization failed", 401, "UNAUTHORIZED")
    return True
