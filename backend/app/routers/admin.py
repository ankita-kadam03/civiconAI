from __future__ import annotations

import json
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Query

from app.config import get_settings
from app.db import Database, get_db
from app.deps import db_dep, require_roles
from app.domain.status import is_open_status
from app.errors import AppError
from app.schemas import CategoryIn, DepartmentIn, EscalationRuleIn, RolePatch
from app.security import now_utc
from app.serialize import dt, user_public
from app.services.ai import ai_service
from app.services.auth_config import jwt_auth_health
from app.services.audit import write_audit
from app.services.pubsub import pubsub_service
from app.services.bigquery_analytics import bigquery_analytics
from app.services.storage import storage_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(user: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep), q: str | None = None):
    docs = list(db.col("users").find({}).sort("created_at", -1))
    if q:
        needle = q.lower()
        docs = [d for d in docs if needle in d.get("email", "").lower() or needle in (d.get("display_name") or "").lower()]
    return [user_public(d) for d in docs]


@router.patch("/users/{user_id}")
def patch_user(user_id: str, body: RolePatch, admin: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    target = db.col("users").find_one({"_id": user_id})
    if not target:
        raise AppError("User not found", 404, "NOT_FOUND")
    if target["_id"] == admin["_id"] and body.role != "ADMIN":
        raise AppError("You cannot remove your own admin role", 400, "FORBIDDEN")
    patch = {"role": body.role, "updated_at": now_utc()}
    if body.department_id is not None:
        patch["department_id"] = body.department_id or None
    if body.is_active is not None:
        patch["is_active"] = body.is_active
    db.col("users").update_one({"_id": user_id}, {"$set": patch})
    write_audit(db, action="user.role", entity_type="user", actor_id=admin["_id"], entity_id=user_id, metadata={"role": body.role})
    return user_public(db.col("users").find_one({"_id": user_id}))


@router.get("/officers")
def officers(user: dict = Depends(require_roles("ADMIN", "OFFICER")), db: Database = Depends(db_dep)):
    docs = db.col("users").find({"role": {"$in": ["OFFICER", "ADMIN"]}, "is_active": True})
    return [user_public(d) for d in docs]


@router.get("/categories")
def categories(_: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    return list(_clean_many(db.col("categories").find({})))


@router.post("/categories")
def create_category(body: CategoryIn, admin: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    if db.col("categories").find_one({"slug": body.slug}):
        raise AppError("Category slug already exists", 409, "DUPLICATE")
    doc = {"_id": uuid.uuid4().hex, **body.model_dump(), "created_at": now_utc(), "updated_at": now_utc()}
    db.col("categories").insert_one(doc)
    return _clean(doc)


@router.patch("/categories/{category_id}")
def patch_category(category_id: str, body: CategoryIn, admin: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    if not db.col("categories").find_one({"_id": category_id}):
        raise AppError("Category not found", 404, "NOT_FOUND")
    db.col("categories").update_one({"_id": category_id}, {"$set": {**body.model_dump(), "updated_at": now_utc()}})
    return _clean(db.col("categories").find_one({"_id": category_id}))


@router.get("/departments")
def departments(_: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    return list(_clean_many(db.col("departments").find({})))


@router.patch("/departments/{department_id}")
def patch_department(department_id: str, body: DepartmentIn, admin: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    if not db.col("departments").find_one({"_id": department_id}):
        raise AppError("Department not found", 404, "NOT_FOUND")
    db.col("departments").update_one(
        {"_id": department_id},
        {
            "$set": {
                "name": body.name,
                "code": body.code.upper(),
                "description": body.description,
                "contact_hint": body.contact_hint,
                "updated_at": now_utc(),
            }
        },
    )
    return _clean(db.col("departments").find_one({"_id": department_id}))


@router.post("/departments")
def create_department(body: DepartmentIn, admin: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    if db.col("departments").find_one({"code": body.code.upper()}):
        raise AppError("Department code already exists", 409, "DUPLICATE")
    doc = {
        "_id": uuid.uuid4().hex,
        "name": body.name,
        "code": body.code.upper(),
        "description": body.description,
        "contact_hint": body.contact_hint,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    db.col("departments").insert_one(doc)
    return _clean(doc)


@router.get("/escalation-rules")
def rules(_: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    return list(_clean_many(db.col("escalation_rules").find({})))


@router.post("/escalation-rules")
def create_rule(body: EscalationRuleIn, admin: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    doc = {"_id": uuid.uuid4().hex, **body.model_dump(), "created_at": now_utc()}
    db.col("escalation_rules").insert_one(doc)
    return _clean(doc)


@router.patch("/escalation-rules/{rule_id}")
def patch_rule(rule_id: str, body: EscalationRuleIn, admin: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep)):
    if not db.col("escalation_rules").find_one({"_id": rule_id}):
        raise AppError("Rule not found", 404, "NOT_FOUND")
    db.col("escalation_rules").update_one({"_id": rule_id}, {"$set": body.model_dump()})
    return _clean(db.col("escalation_rules").find_one({"_id": rule_id}))


@router.get("/audit")
def audit_logs(_: dict = Depends(require_roles("ADMIN")), db: Database = Depends(db_dep), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    docs = list(db.col("audit_logs").find({}).sort("created_at", -1))
    total = len(docs)
    start = (page - 1) * page_size
    items = []
    for d in docs[start : start + page_size]:
        try:
            meta = json.loads(d.get("metadata") or "{}")
        except json.JSONDecodeError:
            meta = {}
        items.append(
            {
                "id": d["_id"],
                "action": d.get("action"),
                "entity_type": d.get("entity_type"),
                "entity_id": d.get("entity_id"),
                "actor_id": d.get("actor_id"),
                "metadata": meta,
                "created_at": dt(d.get("created_at")),
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/escalations")
def escalations(_: dict = Depends(require_roles("ADMIN", "OFFICER")), db: Database = Depends(db_dep)):
    docs = list(db.col("escalations").find({}).sort("created_at", -1))
    return [
        {
            "id": d["_id"],
            "incident_id": d.get("incident_id"),
            "level": d.get("level"),
            "reason": d.get("reason"),
            "triggered_by": d.get("triggered_by"),
            "created_at": dt(d.get("created_at")),
        }
        for d in docs
    ]


@router.get("/analytics")
def analytics(_: dict = Depends(require_roles("ADMIN", "OFFICER")), db: Database = Depends(db_dep)):
    incidents = list(db.col("complaints").find({}))
    total = len(incidents)
    open_n = sum(1 for i in incidents if is_open_status(i.get("status", "")))
    resolved = [i for i in incidents if i.get("status") in {"RESOLVED", "CLOSED"}]
    overdue = 0
    now = now_utc()
    for i in incidents:
        if not is_open_status(i.get("status", "")):
            continue
        created = i.get("created_at") or now
        cat = db.col("categories").find_one({"_id": i.get("category_id")}) or {}
        hours = cat.get("resolve_hours") or 168
        if (now - created) > timedelta(hours=hours):
            overdue += 1
    durations = []
    for i in resolved:
        if i.get("resolved_at") and i.get("created_at"):
            durations.append((i["resolved_at"] - i["created_at"]).total_seconds() / 3600)
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_dept: dict[str, int] = {}
    geo = []
    for i in incidents:
        by_status[i.get("status", "UNKNOWN")] = by_status.get(i.get("status", "UNKNOWN"), 0) + 1
        cat = db.col("categories").find_one({"_id": i.get("category_id")}) or {}
        name = cat.get("name") or "Unknown"
        by_category[name] = by_category.get(name, 0) + 1
        dept = db.col("departments").find_one({"_id": i.get("department_id")}) or {}
        dname = dept.get("name") or "Unassigned"
        by_dept[dname] = by_dept.get(dname, 0) + 1
        if i.get("latitude") is not None:
            geo.append({"lat": i["latitude"], "lng": i["longitude"], "status": i.get("status"), "severity": i.get("severity")})
    return {
        "total": total,
        "active": open_n,
        "resolved": len(resolved),
        "overdue": overdue,
        "resolution_rate": (len(resolved) / total) if total else 0,
        "avg_resolution_hours": (sum(durations) / len(durations)) if durations else 0,
        "by_status": by_status,
        "by_category": by_category,
        "by_department": by_dept,
        "geo": geo,
        "hotspots": _hotspots(incidents),
        "department_performance": [
            {
                "department": name,
                "open": sum(
                    1
                    for i in incidents
                    if (db.col("departments").find_one({"_id": i.get("department_id")}) or {}).get("name") == name
                    and is_open_status(i.get("status", ""))
                ),
                "total": count,
            }
            for name, count in by_dept.items()
        ],
        "in_memory_data": get_settings().allow_memory_db or get_db().mode == "memory",
        "bigquery": {
            "enabled": bool(get_settings().bigquery_dataset),
            "recurrence_60d": bigquery_analytics.recurrence_hotspots(),
            "summary": bigquery_analytics.ai_summary_context(),
        },
        "ai_platform": "Gemini / Vertex AI (required for classification)",
    }


@router.get("/integrations")
def integrations(_: dict = Depends(require_roles("ADMIN"))):
    settings = get_settings()
    db = get_db()
    return {
        "firestore": {
            "status": "connected" if db.mode == "firestore" else "in_memory",
            "configured": bool(settings.firebase_project_resolved),
            "project": settings.firebase_project_resolved or None,
            "error": db.error,
        },
        "gcs": storage_service.health(),
        "pubsub": pubsub_service.health(),
        "ai": ai_service.health(),
        "maps": {"status": "frontend_key", "note": "Browser Maps key is configured separately"},
        "adc": {"status": "used_when_no_api_key", "project_configured": bool(settings.google_cloud_project)},
        "bigquery": bigquery_analytics.health(),
        "required_integrations": {
            "require_gemini": settings.require_gemini,
            "require_bigquery": settings.require_bigquery,
            "gemini_configured": bool(settings.gemini_api_key.strip()) or bool(settings.google_cloud_project.strip()),
        },
        "fcm": {"configured": bool(settings.firebase_project_resolved)},
        "auth": jwt_auth_health(settings),
        "weather": {
            "provider": "google_weather",
            "server_key_configured": bool(settings.google_server_api_key.strip() or settings.google_maps_api_key.strip()),
            "hint": "Enable Weather API and set GOOGLE_SERVER_API_KEY (server key, not browser referrer key).",
        },
        "pubsub_usage": "Publishes incident.created and incident.status_changed on complaint create/update; internal push handler runs escalations.",
    }


def _hotspots(incidents: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for item in incidents:
        key = item.get("locality") or "Unknown"
        counts[key] = counts.get(key, 0) + 1
    return sorted(
        [{"locality": name, "count": count} for name, count in counts.items()],
        key=lambda row: (-row["count"], row["locality"]),
    )[:8]


def _clean(doc: dict | None) -> dict | None:
    if not doc:
        return None
    out = dict(doc)
    out["id"] = out.pop("_id", None)
    for key in ("created_at", "updated_at"):
        if key in out:
            out[key] = dt(out[key])
    return out


def _clean_many(docs) -> list[dict]:
    return [_clean(d) for d in docs if d]
