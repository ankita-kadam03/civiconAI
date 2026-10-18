from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db import Database
from app.deps import db_dep, optional_user
from app.errors import AppError
from app.serialize import complaint_public, dt, serialize_comments, user_has_promoted
from app.services.storage import storage_service

router = APIRouter(tags=["public"])


def _enrich(db: Database, doc: dict, include_internal: bool = False) -> dict:
    cat = db.col("categories").find_one({"_id": doc.get("category_id")}) or {}
    dept = db.col("departments").find_one({"_id": doc.get("department_id")}) or {}
    extras = {
        "category": {"id": cat.get("_id"), "name": cat.get("name"), "slug": cat.get("slug"), "icon": cat.get("icon")},
        "department": {"id": dept.get("_id"), "name": dept.get("name"), "code": dept.get("code")} if dept else None,
    }
    return complaint_public(doc, include_internal=include_internal, extras=extras)


@router.get("/api/public/categories")
def public_categories(db: Database = Depends(db_dep)):
    items = list(db.col("categories").find({"is_active": True}))
    return [
        {
            "id": c["_id"],
            "name": c["name"],
            "slug": c["slug"],
            "icon": c.get("icon"),
            "description": c.get("description"),
            "department_id": c.get("department_id"),
        }
        for c in items
    ]


@router.get("/api/public/departments")
def public_departments(db: Database = Depends(db_dep)):
    return [
        {
            "id": d["_id"],
            "name": d["name"],
            "code": d["code"],
            "description": d.get("description"),
            "contact_hint": d.get("contact_hint"),
        }
        for d in db.col("departments").find({})
    ]


@router.get("/api/public/localities")
def public_localities(db: Database = Depends(db_dep)):
    regions = list(db.col("regions").find({"is_active": True}).sort("level", 1))
    regions.sort(key=lambda r: (r.get("level") or 0, (r.get("name") or "").lower()))
    if regions:
        out: list[dict] = []
        for r in regions:
            level = int(r.get("level") or 0)
            prefix = {3: "Municipality", 2: "District", 1: "Ward"}.get(level, "Area")
            name = r.get("name") or r.get("code") or "Area"
            out.append(
                {
                    "id": r["_id"],
                    "code": r.get("code"),
                    "name": f"{prefix}: {name}" if level in {1, 2, 3} else name,
                    "level": level,
                }
            )
        return out
    return [
        {"id": "tambaram", "code": "tambaram", "name": "Municipality: Tambaram City Municipal Corporation", "level": 3},
        {"id": "chengalpattu", "code": "chengalpattu", "name": "District: Chengalpattu", "level": 2},
        {"id": "old-pallavaram-area-a", "code": "old-pallavaram-area-a", "name": "Ward: Old Pallavaram - Area A", "level": 1},
        {"id": "old-pallavaram-area-b", "code": "old-pallavaram-area-b", "name": "Ward: Old Pallavaram - Area B", "level": 1},
    ]


@router.get("/api/public/complaints")
def public_complaints(
    db: Database = Depends(db_dep),
    q: str | None = None,
    category: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query: dict = {"is_public": True}
    if status:
        query["status"] = status
    if category:
        cat = db.col("categories").find_one({"$or": [{"_id": category}, {"slug": category}]})
        if cat:
            query["category_id"] = cat["_id"]
    docs = list(db.col("complaints").find(query).sort("created_at", -1))
    if q:
        needle = q.lower()
        docs = [d for d in docs if needle in (d.get("title") or "").lower() or needle in (d.get("reference") or "").lower() or needle in (d.get("locality") or "").lower()]
    total = len(docs)
    start = (page - 1) * page_size
    items = [_enrich(db, d, False) for d in docs[start : start + page_size]]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/api/public/complaints/{reference}")
def public_complaint(
    reference: str,
    db: Database = Depends(db_dep),
    user: dict | None = Depends(optional_user),
):
    doc = db.col("complaints").find_one({"$or": [{"reference": reference.upper()}, {"_id": reference}], "is_public": True})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    history = list(db.col("complaint_status_history").find({"incident_id": doc["_id"]}).sort("created_at", 1))
    attachments = [
        a
        for a in db.col("attachments").find({"incident_id": doc["_id"], "is_private": False})
    ]
    comments = list(db.col("comments").find({"incident_id": doc["_id"], "is_internal": False}).sort("created_at", 1))
    body = _enrich(db, doc, False)
    body["history"] = [
        {"id": h["_id"], "from_status": h.get("from_status"), "to_status": h.get("to_status"), "created_at": dt(h.get("created_at"))}
        for h in history
    ]
    body["attachments"] = [{"id": a["_id"], "kind": a.get("kind")} for a in attachments]
    body["comments"] = serialize_comments(db, comments)
    if user:
        body["viewer_has_promoted"] = user_has_promoted(db, doc["_id"], user["_id"])
    return body


@router.get("/api/public/attachments/{attachment_id}")
def public_attachment(attachment_id: str, db: Database = Depends(db_dep)):
    from fastapi.responses import Response

    att = db.col("attachments").find_one({"_id": attachment_id})
    if not att or att.get("is_private", True):
        raise AppError("Attachment not found", 404, "NOT_FOUND")
    incident = db.col("complaints").find_one({"_id": att["incident_id"]})
    if not incident or not incident.get("is_public"):
        raise AppError("Attachment not found", 404, "NOT_FOUND")
    data = storage_service.load(att["object_key"])
    return Response(content=data, media_type=att.get("mime_type") or "application/octet-stream")


@router.get("/api/public/config")
def public_config(db: Database = Depends(db_dep)):
    from app.config import get_settings

    settings = get_settings()
    return {
        "service": "civicon-api",
        "memory_database": settings.allow_memory_db,
        "database": db.mode,
        "firestore_project": settings.firebase_project_resolved or None,
        "ai_fallback": True,
    }


@router.get("/api/public/weather")
def public_weather(lat: float = Query(..., ge=-90, le=90), lng: float = Query(..., ge=-180, le=180)):
    from app.services.weather_client import fetch_current

    return fetch_current(lat, lng)


@router.get("/api/public/bootstrap")
def public_bootstrap(db: Database = Depends(db_dep)):
    from app.config import get_settings
    from app.integrations import pubsub_service
    from app.services.storage import storage_service

    from app.services.regions import municipality_region, service_area_payload

    settings = get_settings()
    muni = municipality_region(db)
    officers = []
    if settings.seed_bootstrap_users.lower() == "yes":
        for doc in db.col("users").find({"bootstrap_account": True}).sort("authority_level", 1):
            reg = db.col("regions").find_one({"_id": doc.get("region_id")}) if doc.get("region_id") else muni
            officers.append(
                {
                    "email": doc["email"],
                    "role": doc.get("role"),
                    "authority_level": doc.get("authority_level"),
                    "region": reg.get("name") if reg else None,
                    "home": {"lat": doc.get("home_latitude"), "lng": doc.get("home_longitude")},
                }
            )
    center = settings.map_center
    if not center and muni and muni.get("latitude") is not None and muni.get("longitude") is not None:
        center = (float(muni["latitude"]), float(muni["longitude"]))
    area = service_area_payload(db)
    return {
        "service_area": {
            "name": muni.get("name") if muni else settings.service_area_name or "Service area",
            "code": muni.get("code") if muni else settings.service_area_code,
            **area,
        },
        "google_cloud": {
            "project": settings.google_cloud_project or None,
            "location": settings.google_cloud_location,
        },
        "map_center": {"lat": center[0], "lng": center[1]} if center else None,
        "integrations": {
            "gcs": storage_service.health(),
            "pubsub": pubsub_service.health(),
            "weather": {
                "configured": bool((settings.google_server_api_key or settings.google_maps_api_key or "").strip()),
                "provider": "google_weather",
            },
            "fcm": {"configured": bool(settings.firebase_project_resolved)},
        },
        "push_note": "In-app notifications are stored in the database. Browser push (FCM) requires Firebase Cloud Messaging and a registered service worker.",
        "pubsub_note": "The API publishes incident.created and incident.status_changed to PUBSUB_TOPIC_EVENTS when Pub/Sub is configured. Subscribers are not required for the web UI.",
        "test_accounts": officers,
    }


@router.get("/health")
def health(db: Database = Depends(db_dep)):
    from app.config import get_settings

    settings = get_settings()
    return {
        "ok": True,
        "service": "civicon-api",
        "memory_database": settings.allow_memory_db,
        "database": db.mode,
        "firestore_project": settings.firebase_project_resolved or None,
    }


@router.get("/ready")
def ready(db: Database = Depends(db_dep)):
    return {"ok": db.connected, "database": db.mode, "error": db.error}
