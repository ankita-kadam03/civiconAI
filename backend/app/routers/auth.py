from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.db import Database
from app.deps import current_user, db_dep
from app.errors import AppError
from app.schemas import ForgotIn, LoginIn, PasswordChangeIn, RefreshIn, ResetIn, SignupIn
from app.security import (
    access_token,
    encode_token,
    hash_password,
    now_utc,
    refresh_token,
    reset_token,
    sha256,
    verify_password,
    decode_token,
)
from app.serialize import user_public
from app.services.audit import write_audit

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _tokens(user: dict) -> dict:
    return {
        "access_token": access_token(user["_id"], user["role"]),
        "refresh_token": refresh_token(user["_id"]),
        "token_type": "bearer",
        "user": user_public(user),
    }


@router.post("/signup")
def signup(body: SignupIn, request: Request, db: Database = Depends(db_dep)):
    existing = db.col("users").find_one({"email": body.email.lower()})
    if existing:
        raise AppError("An account with this email already exists", 409, "EMAIL_TAKEN")
    user = {
        "_id": uuid.uuid4().hex,
        "email": body.email.lower(),
        "display_name": body.display_name.strip(),
        "phone": body.phone,
        "role": "CITIZEN",
        "department_id": None,
        "locality": body.locality,
        "password_hash": hash_password(body.password),
        "is_active": True,
        "demo_account": False,
        "fcm_tokens": [],
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    db.col("users").insert_one(user)
    write_audit(db, action="auth.signup", entity_type="user", actor_id=user["_id"], entity_id=user["_id"], ip=request.client.host if request.client else None)
    return _tokens(user)


@router.post("/login")
def login(body: LoginIn, request: Request, db: Database = Depends(db_dep)):
    user = db.col("users").find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user.get("password_hash") or ""):
        raise AppError("Email or password is incorrect", 401, "INVALID_CREDENTIALS")
    if not user.get("is_active", True):
        raise AppError("This account is disabled", 403, "DISABLED")
    write_audit(db, action="auth.login", entity_type="user", actor_id=user["_id"], entity_id=user["_id"], ip=request.client.host if request.client else None)
    return _tokens(user)


@router.post("/refresh")
def refresh(body: RefreshIn, db: Database = Depends(db_dep)):
    if not body.refresh_token:
        raise AppError("Refresh token required", 401, "UNAUTHORIZED")
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise AppError("Refresh token is invalid", 401, "UNAUTHORIZED") from None
    if payload.get("typ") != "refresh":
        raise AppError("Refresh token is invalid", 401, "UNAUTHORIZED")
    user = db.col("users").find_one({"_id": payload.get("sub")})
    if not user or not user.get("is_active", True):
        raise AppError("Account is not available", 401, "UNAUTHORIZED")
    return _tokens(user)


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user_public(user)


@router.post("/forgot-password")
def forgot(body: ForgotIn, db: Database = Depends(db_dep)):
    settings = get_settings()
    user = db.col("users").find_one({"email": body.email.lower()})
    # Always look the same to the caller.
    token_out = None
    if user:
        raw = reset_token()
        db.col("password_resets").insert_one(
            {
                "_id": uuid.uuid4().hex,
                "user_id": user["_id"],
                "token_hash": sha256(raw),
                "expires_at": now_utc() + timedelta(hours=2),
                "used": False,
                "created_at": now_utc(),
            }
        )
        if settings.app_env.lower() != "production" and settings.expose_password_reset_token:
            token_out = raw
    return {
        "ok": True,
        "message": "If that email is registered, a reset link will be issued.",
        "reset_token": token_out,
        "dev_reset_token": bool(token_out),
    }


@router.post("/reset-password")
def reset(body: ResetIn, db: Database = Depends(db_dep)):
    record = db.col("password_resets").find_one({"token_hash": sha256(body.token), "used": False})
    if not record or record["expires_at"] < now_utc():
        raise AppError("This reset link is invalid or expired", 400, "RESET_INVALID")
    db.col("users").update_one({"_id": record["user_id"]}, {"$set": {"password_hash": hash_password(body.password), "updated_at": now_utc()}})
    db.col("password_resets").update_one({"_id": record["_id"]}, {"$set": {"used": True}})
    return {"ok": True}


@router.post("/change-password")
def change_password(body: PasswordChangeIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    if not verify_password(body.current_password, user.get("password_hash") or ""):
        raise AppError("Current password is incorrect", 400, "INVALID_CREDENTIALS")
    db.col("users").update_one({"_id": user["_id"]}, {"$set": {"password_hash": hash_password(body.new_password), "updated_at": now_utc()}})
    return {"ok": True}


@router.post("/logout")
def logout():
    return {"ok": True}
