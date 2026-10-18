from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db import Database
from app.deps import current_user, db_dep, require_roles
from app.domain.geo import encode_geohash
from app.errors import AppError
from app.schemas import SavedLocationIn, VerifyIn
from app.security import now_utc
from app.serialize import dt
from app.services.community import claim, currently_better, promote, verify
from app.services.priority import score_incident

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.post("/incidents/{incident_id}/promote")
def v1_promote(incident_id: str, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    return promote(db, incident_id, user["_id"])


@router.post("/incidents/{incident_id}/better")
def v1_better(incident_id: str, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    return currently_better(db, incident_id, user["_id"])


@router.post("/incidents/{incident_id}/verify")
def v1_verify(incident_id: str, body: VerifyIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    return verify(db, incident_id, user["_id"], body.answer)


@router.post("/admin/incidents/{incident_id}/claim")
def v1_claim(incident_id: str, user: dict = Depends(require_roles("OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3")), db: Database = Depends(db_dep)):
    return claim(db, incident_id, user["_id"])


@router.post("/me/saved-locations")
def save_location(body: SavedLocationIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    from app.services.regions import assert_in_municipality

    assert_in_municipality(db, body.lat, body.lng)
    rec = {
        "_id": f"{user['_id']}:{now_utc().timestamp()}",
        "user_id": user["_id"],
        "label": body.label[:80],
        "lat": body.lat,
        "lng": body.lng,
        "geohash": encode_geohash(body.lat, body.lng),
        "radius_m": body.radius_m,
        "alerts": {"incidents": True, "weather": True},
        "created_at": now_utc(),
    }
    db.col("saved_locations").insert_one(rec)
    rec["id"] = rec.pop("_id")
    rec["created_at"] = dt(rec["created_at"])
    return rec


@router.get("/me/saved-locations")
def list_locations(user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    items = []
    for rec in db.col("saved_locations").find({"user_id": user["_id"]}):
        rec["id"] = rec.pop("_id")
        rec["created_at"] = dt(rec.get("created_at"))
        items.append(rec)
    return {"items": items}


@router.delete("/me/saved-locations/{location_id}")
def delete_location(location_id: str, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    rec = db.col("saved_locations").find_one({"_id": location_id, "user_id": user["_id"]})
    if not rec:
        raise AppError("Saved place not found", 404, "NOT_FOUND")
    db.col("saved_locations").delete_one({"_id": location_id})
    return {"ok": True}


@router.put("/me/notification-prefs")
def prefs(body: dict, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    db.col("users").update_one({"_id": user["_id"]}, {"$set": {"notification_prefs": body, "updated_at": now_utc()}})
    return {"ok": True}


@router.get("/notifications")
def v1_notifications(
    user: dict = Depends(current_user),
    db: Database = Depends(db_dep),
    tab: str = Query("for_you"),
):
    docs = list(db.col("notifications").find({"user_id": user["_id"]}).sort("created_at", -1))
    if tab == "alerts":
        docs = [d for d in docs if d.get("type") in {"R1", "R2", "ESCALATED", "WEATHER"}]
    elif tab == "nearby":
        docs = [d for d in docs if d.get("type") in {"NEARBY", "WEATHER", "REPORT_SUBMITTED"}]
    elif tab == "inbox":
        docs = [d for d in docs if d.get("type") in {"ASSIGNED", "ESCALATED", "R1", "R2", "SLA"}]
    elif tab in {"overdue", "escalated"}:
        docs = [d for d in docs if d.get("type") in {"ESCALATED", "SLA", "R1", "R4", "REOPENED"}]
    elif tab == "persistent":
        docs = [d for d in docs if d.get("type") in {"ESCALATED", "REOPENED"}]
    elif tab == "new_in_region":
        docs = [d for d in docs if d.get("type") in {"REPORT_SUBMITTED", "NEARBY", "R1", "R2"}]
    elif tab == "digest":
        docs = docs[:20]
    elif tab == "for_you":
        docs = [d for d in docs if d.get("type") not in {"NEARBY"}]
    unread = sum(1 for d in docs if not d.get("read_at"))
    return {
        "items": [
            {
                "id": d["_id"],
                "type": d.get("type"),
                "title": d.get("title"),
                "body": d.get("body"),
                "incident_id": d.get("incident_id"),
                "read_at": dt(d.get("read_at")),
                "created_at": dt(d.get("created_at")),
            }
            for d in docs[:50]
        ],
        "unread": unread,
        "tab": tab,
        "realtime": "poll",
    }


@router.post("/incidents/{incident_id}/score")
def rescore(incident_id: str, user: dict = Depends(require_roles("OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3")), db: Database = Depends(db_dep)):
    return score_incident(db, incident_id) or {}
