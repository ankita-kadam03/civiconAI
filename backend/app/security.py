from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGO = "HS256"


def hash_password(password: str) -> str:
    return pwd.hash(password[:72])


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd.verify(password[:72], hashed)
    except Exception:
        return False


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def encode_token(payload: dict[str, Any], minutes: int | None = None, days: int | None = None) -> str:
    settings = get_settings()
    exp = now_utc()
    if minutes is not None:
        exp += timedelta(minutes=minutes)
    elif days is not None:
        exp += timedelta(days=days)
    else:
        exp += timedelta(minutes=settings.jwt_access_minutes)
    body = {**payload, "exp": exp, "iat": now_utc()}
    return jwt.encode(body, settings.signing_secret, algorithm=ALGO)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.signing_secret, algorithms=[ALGO])


def access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    return encode_token({"sub": user_id, "role": role, "typ": "access"}, minutes=settings.jwt_access_minutes)


def refresh_token(user_id: str) -> str:
    settings = get_settings()
    return encode_token({"sub": user_id, "typ": "refresh", "jti": secrets.token_hex(8)}, days=settings.jwt_refresh_days)


def reset_token() -> str:
    return secrets.token_urlsafe(32)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def submission_hash(reporter_id: str, title: str, category_id: str, lat: float | None, lng: float | None, occurred_date: str) -> str:
    lat_s = f"{round(lat, 3)}" if lat is not None else ""
    lng_s = f"{round(lng, 3)}" if lng is not None else ""
    raw = "|".join([reporter_id, title.strip().lower(), category_id, lat_s, lng_s, occurred_date])
    return sha256(raw)
