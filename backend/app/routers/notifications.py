from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db import Database
from app.deps import current_user, db_dep
from app.security import now_utc
from app.serialize import dt

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    user: dict = Depends(current_user),
    db: Database = Depends(db_dep),
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
):
    query: dict = {"user_id": user["_id"]}
    docs = list(db.col("notifications").find(query).sort("created_at", -1))
    if unread_only:
        docs = [d for d in docs if not d.get("read_at")]
    total = len(docs)
    start = (page - 1) * page_size
    items = [
        {
            "id": d["_id"],
            "type": d.get("type"),
            "title": d.get("title"),
            "body": d.get("body"),
            "incident_id": d.get("incident_id"),
            "read_at": dt(d.get("read_at")),
            "created_at": dt(d.get("created_at")),
        }
        for d in docs[start : start + page_size]
    ]
    unread = db.col("notifications").count_documents({"user_id": user["_id"], "read_at": None})
    return {"items": items, "total": total, "unread": unread, "page": page, "page_size": page_size}


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    db.col("notifications").update_one(
        {"_id": notification_id, "user_id": user["_id"]},
        {"$set": {"read_at": now_utc()}},
    )
    return {"ok": True}


@router.post("/read-all")
def read_all(user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    db.col("notifications").update_many({"user_id": user["_id"], "read_at": None}, {"$set": {"read_at": now_utc()}})
    return {"ok": True}
