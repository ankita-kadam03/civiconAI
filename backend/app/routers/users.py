from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db import Database
from app.deps import current_user, db_dep
from app.schemas import FcmTokenIn, ProfilePatch
from app.security import now_utc
from app.serialize import user_public
from app.services.notifications import notify
from app.services.weather_client import fetch_current

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
def get_me(user: dict = Depends(current_user)):
    return user_public(user)


@router.patch("/me")
def patch_me(body: ProfilePatch, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if patch:
        patch["updated_at"] = now_utc()
        db.col("users").update_one({"_id": user["_id"]}, {"$set": patch})
        user = db.col("users").find_one({"_id": user["_id"]})
    return user_public(user)


class WeatherCheckIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@router.post("/me/weather-check")
def weather_check(body: WeatherCheckIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    payload = fetch_current(body.latitude, body.longitude)
    if not payload.get("ok"):
        return payload
    alert = payload.get("alert")
    if alert:
        from app.security import now_utc

        day = now_utc().date().isoformat()
        notify(
            db,
            user_id=user["_id"],
            ntype="WEATHER",
            title=payload.get("headline") or "Weather advisory",
            body=payload.get("message") or "Check conditions near you.",
            dedupe_key=f"weather:{user['_id']}:{alert}:{day}",
        )
    return payload


@router.post("/me/fcm-token")
def fcm_token(body: FcmTokenIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    tokens = list(user.get("fcm_tokens") or [])
    if body.token not in tokens:
        tokens.append(body.token)
        db.col("users").update_one({"_id": user["_id"]}, {"$set": {"fcm_tokens": tokens[-10:]}})
    return {"ok": True}
