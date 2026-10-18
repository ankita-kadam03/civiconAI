from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import Database
from app.deps import current_user, db_dep
from app.schemas import FcmTokenIn, ProfilePatch
from app.security import now_utc
from app.serialize import user_public

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


@router.post("/me/fcm-token")
def fcm_token(body: FcmTokenIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    tokens = list(user.get("fcm_tokens") or [])
    if body.token not in tokens:
        tokens.append(body.token)
        db.col("users").update_one({"_id": user["_id"]}, {"$set": {"fcm_tokens": tokens[-10:]}})
    return {"ok": True}
