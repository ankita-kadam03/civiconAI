from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from starlette.datastructures import UploadFile as FormUploadFile

from app.db import Database
from app.deps import current_user, db_dep, principal_of
from app.domain.files import MAX_FILE_BYTES, validate_upload
from app.domain.ai_validate import validate_classification
from app.domain.rbac import can_update_incident, can_view_internal_notes, can_view_report_sensitive
from app.domain.report_images import MAX_REPORT_ATTACHMENTS, read_report_images, report_analysis_digest
from app.domain.status import assert_transition, can_transition
from app.errors import AppError
from app.schemas import AssignIn, CommentIn, ComplaintCreate, EscalateIn, StatusUpdateIn
from app.security import decode_token, now_utc, submission_hash
from app.serialize import attachment_public, complaint_public, dt, serialize_comments, user_has_promoted
from app.services.ai import ai_service, similar_score
from app.services.audit import write_audit
from app.services.escalation import apply_decision
from app.domain.escalation import EscalationDecision
from app.services.notifications import notify
from app.services.pubsub import pubsub_service
from app.services.storage import storage_service

router = APIRouter(tags=["complaints"])


def _sync_bigquery(db: Database, doc: dict) -> None:
    from app.services.bigquery_analytics import bigquery_analytics

    if not doc:
        return
    cat = db.col("categories").find_one({"_id": doc.get("category_id")}) or {}
    dept = db.col("departments").find_one({"_id": doc.get("department_id")}) or {}
    try:
        bigquery_analytics.sync_incident(
            doc,
            category_name=cat.get("name"),
            department_name=dept.get("name"),
        )
    except Exception:  # noqa: BLE001
        pass


def _next_reference(db: Database) -> str:
    year = now_utc().year
    n = db.col("complaints").count_documents({}) + 1
    for _ in range(20):
        ref = f"CIV-{year}-{100000 + n}"
        if not db.col("complaints").find_one({"reference": ref}):
            return ref
        n += 1
    return f"CIV-{year}-{uuid.uuid4().hex[:8].upper()}"


def _enrich(db: Database, doc: dict, principal) -> dict:
    include = can_view_report_sensitive(principal, doc)
    cat = db.col("categories").find_one({"_id": doc.get("category_id")}) or {}
    dept = db.col("departments").find_one({"_id": doc.get("department_id")}) or {}
    reporter = db.col("users").find_one({"_id": doc.get("reporter_id")}) or {}
    officer = db.col("users").find_one({"_id": doc.get("assigned_officer_id")}) if doc.get("assigned_officer_id") else None
    claimed = db.col("users").find_one({"_id": doc.get("claimed_by")}) if doc.get("claimed_by") else None
    contact_officer = officer or claimed
    reporter_out = None
    if reporter and include:
        reporter_out = {
            "id": reporter.get("_id"),
            "display_name": reporter.get("display_name"),
            "phone": reporter.get("phone"),
        }
    assignee_out = None
    if contact_officer:
        assignee_out = {
            "id": contact_officer.get("_id"),
            "display_name": contact_officer.get("display_name"),
            "phone": contact_officer.get("phone") if include else None,
        }
    from app.services.regions import municipality_region

    municipality = municipality_region(db) or {}
    extras = {
        "category": {"id": cat.get("_id"), "name": cat.get("name"), "slug": cat.get("slug"), "icon": cat.get("icon")},
        "department": {"id": dept.get("_id"), "name": dept.get("name"), "code": dept.get("code")} if dept else None,
        "reporter": reporter_out,
        "assignee": assignee_out,
        "municipality_name": municipality.get("name"),
    }
    return complaint_public(doc, signed_in=True, include_internal=include, extras=extras)


def _visible_query(user: dict) -> dict:
    if user["role"] in {"ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3", "OFFICER"}:
        return {}
    return {"reporter_id": user["_id"]}


@router.post("/api/complaints")
async def create_complaint(request: Request, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    from app.services.regions import assert_in_municipality

    images: list[tuple[bytes, str, str]] = []
    classification_token = ""
    keep_attachments_private = False
    content_type = request.headers.get("content-type", "")
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            report_json = form.get("report")
            if not isinstance(report_json, str):
                raise AppError("Report details are required.", 400, "INVALID_REPORT")
            body = ComplaintCreate.model_validate_json(report_json)
            file_values = form.getlist("files")
            if any(not isinstance(value, FormUploadFile) for value in file_values):
                raise AppError("Each report attachment must be an image file.", 400, "INVALID_FILE")
            uploads = [value for value in file_values if isinstance(value, FormUploadFile)]
            images = await read_report_images(uploads)
            classification_token = str(form.get("classification_token") or "")
            keep_attachments_private = str(form.get("keep_attachments_private") or "").lower() in {"true", "1", "on"}
        elif content_type.startswith("application/json"):
            body = ComplaintCreate.model_validate(await request.json())
        else:
            raise AppError("Send report details as JSON or multipart form data.", 415, "UNSUPPORTED_MEDIA_TYPE")
    except ValidationError as exc:
        raise AppError(str(exc), 422, "INVALID_REPORT") from exc
    except ValueError as exc:
        raise AppError("Report details must be valid JSON.", 422, "INVALID_REPORT") from exc

    cat = db.col("categories").find_one({"_id": body.category_id, "is_active": True})
    if not cat:
        raise AppError("Please choose a valid category", 400, "INVALID_CATEGORY")
    assert_in_municipality(db, body.latitude, body.longitude)
    occurred = body.occurred_at or now_utc()
    digest = submission_hash(
        user["_id"],
        body.title,
        body.category_id,
        body.latitude,
        body.longitude,
        occurred.date().isoformat(),
    )
    existing = db.col("complaints").find_one({"submission_hash": digest, "reporter_id": user["_id"]})
    if existing:
        raise AppError("This looks like a duplicate of a report you already submitted today.", 409, "DUPLICATE")
    classification: dict
    if classification_token:
        try:
            claims = decode_token(classification_token)
        except jwt.InvalidTokenError as exc:
            raise AppError("The report analysis expired or is invalid. Review the report again.", 400, "INVALID_AI_DRAFT") from exc
        raw_classification = claims.get("result")
        expected_digest = report_analysis_digest(body.title, body.description, body.locality, images)
        if (
            claims.get("typ") != "report-classification"
            or claims.get("sub") != user["_id"]
            or claims.get("digest") != expected_digest
            or not isinstance(raw_classification, dict)
        ):
            raise AppError("The report changed after its AI review. Review it again before submitting.", 400, "STALE_AI_DRAFT")
        validated = validate_classification(raw_classification, fallback_title=body.title)
        if validated:
            classification = {
                **validated,
                "source": raw_classification.get("source"),
                "ai_generated": raw_classification.get("ai_generated") is True,
            }
        else:
            raise AppError("The report analysis is invalid. Review it again before submitting.", 400, "INVALID_AI_DRAFT")
    else:
        classification = ai_service.classify(
            body.title,
            body.description,
            body.locality,
            photo_count=len(images) or body.photo_count or 0,
            images=[(data, mime_type) for data, mime_type, _ in images],
        )
    if classification.get("source") == "error":
        raise AppError(
            classification.get("rationale") or "Gemini classification is required but unavailable.",
            503,
            "AI_UNAVAILABLE",
        )
    dept = db.col("departments").find_one({"_id": cat.get("department_id")}) or db.col("departments").find_one(
        {"code": classification.get("department_code")}
    )
    cid = uuid.uuid4().hex
    now = now_utc()
    doc = {
        "_id": cid,
        "reference": _next_reference(db),
        "title": body.title,
        "description": body.description,
        "summary": (body.description or body.title).strip()[:600],
        "category_id": cat["_id"],
        "department_id": dept["_id"] if dept else cat.get("department_id"),
        "status": "SUBMITTED",
        "severity": classification.get("severity") or "MEDIUM",
        "locality": body.locality,
        "address": body.address,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "occurred_at": occurred,
        "reporter_id": user["_id"],
        "assigned_officer_id": None,
        "is_public": True,
        "duplicate_of_id": None,
        "ai_summary": classification.get("summary"),
        "attachment_inference": classification.get("attachment_inference") or None,
        "ai_category_slug": classification.get("category_slug"),
        "ai_severity": classification.get("severity"),
        "ai_department_code": classification.get("department_code"),
        "ai_rationale": (
            "No Summary"
            if not classification.get("ai_generated")
            else classification.get("rationale")
        ),
        "submission_hash": digest,
        "resolved_at": None,
        "last_progress_at": now,
        "created_at": now,
        "updated_at": now,
        "source": "user",
        "escalation_level": 1,
        "counters": {"unique_reporters": 1, "promotes": 0, "better": 0, "yes": 0, "no": 0, "comments": 0},
        "weather_multiplier": 1.0,
        "geohash": None,
        "location": (
            {"type": "Point", "coordinates": [body.longitude, body.latitude]}
            if body.latitude is not None and body.longitude is not None
            else None
        ),
    }
    similars = []
    for other in db.col("complaints").find({"status": {"$in": ["SUBMITTED", "ACKNOWLEDGED", "IN_PROGRESS", "ESCALATED"]}}):
        if other["_id"] == cid:
            continue
        score = similar_score(doc, other)
        if score >= 0.55:
            similars.append({"id": other["_id"], "reference": other.get("reference"), "title": other.get("title"), "score": round(score, 2)})
    similars.sort(key=lambda s: s["score"], reverse=True)
    db.col("complaints").insert_one(doc)
    for data, mime_type, original_name in images:
        object_key = storage_service.save(data, mime_type, original_name, "complaints/report")
        attachment = {
            "_id": uuid.uuid4().hex,
            "incident_id": cid,
            "kind": "report",
            "object_key": object_key,
            "original_name": original_name,
            "mime_type": mime_type,
            "size_bytes": len(data),
            "is_private": keep_attachments_private,
            "uploaded_by_id": user["_id"],
            "created_at": now,
        }
        db.col("attachments").insert_one(attachment)
    db.col("complaint_status_history").insert_one(
        {
            "_id": uuid.uuid4().hex,
            "incident_id": cid,
            "from_status": None,
            "to_status": "SUBMITTED",
            "note": "Citizen submitted a report",
            "actor_id": user["_id"],
            "created_at": now,
        }
    )
    notify(
        db,
        user_id=user["_id"],
        ntype="REPORT_SUBMITTED",
        title="We received your report",
        body=f"Your reference is {doc['reference']}.",
        incident_id=cid,
        dedupe_key=f"submitted:{cid}",
    )
    for staff in db.col("users").find(
        {"role": {"$in": ["OFFICER", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3", "ADMIN"]}, "is_active": True}
    ):
        notify(
            db,
            user_id=staff["_id"],
            ntype="NEW_REPORT",
            title="New civic report",
            body=f"{doc['reference']}: {doc['title'][:80]}",
            incident_id=cid,
            dedupe_key=f"staff-new:{cid}:{staff['_id']}",
        )
    write_audit(db, action="incident.created", entity_type="complaint", actor_id=user["_id"], entity_id=cid, ip=request.client.host if request.client else None)
    pubsub_service.publish("incident.created", {"incident_id": cid, "reference": doc["reference"]})
    from app.domain.geo import encode_geohash
    from app.services.priority import add_report, score_incident

    if body.latitude is not None and body.longitude is not None:
        db.col("complaints").update_one({"_id": cid}, {"$set": {"geohash": encode_geohash(body.latitude, body.longitude)}})
    add_report(db, cid, user["_id"], body.description, now=now)
    score_incident(db, cid, now=now)
    doc = db.col("complaints").find_one({"_id": cid}) or doc
    _sync_bigquery(db, doc)
    out = _enrich(db, doc, principal_of(user))
    out["similar"] = similars[:5]
    out["ai"] = {**classification, "human_override": False}
    return out


@router.get("/api/complaints")
def list_complaints(
    user: dict = Depends(current_user),
    db: Database = Depends(db_dep),
    status: str | None = None,
    category: str | None = None,
    mine: bool = False,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = _visible_query(user)
    if mine:
        query = {"reporter_id": user["_id"]}
    if status:
        query = {"$and": [query, {"status": status}]} if query else {"status": status}
    if category:
        cat = db.col("categories").find_one({"$or": [{"_id": category}, {"slug": category}]})
        if cat:
            extra = {"category_id": cat["_id"]}
            query = {"$and": [query, extra]} if query else extra
    docs = list(db.col("complaints").find(query).sort("created_at", -1))
    if q:
        needle = q.lower()
        docs = [
            d
            for d in docs
            if needle in (d.get("title") or "").lower()
            or needle in (d.get("reference") or "").lower()
            or needle in (d.get("locality") or "").lower()
        ]
    total = len(docs)
    start = (page - 1) * page_size
    principal = principal_of(user)
    items = [_enrich(db, d, principal) for d in docs[start : start + page_size]]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/api/complaints/{incident_id}")
def get_complaint(incident_id: str, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    doc = db.col("complaints").find_one({"$or": [{"_id": incident_id}, {"reference": incident_id.upper()}]})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    principal = principal_of(user)
    include_internal = can_view_internal_notes(principal)
    participant = can_view_report_sensitive(principal, doc)
    history = list(db.col("complaint_status_history").find({"incident_id": doc["_id"]}).sort("created_at", 1))
    comments = list(db.col("comments").find({"incident_id": doc["_id"]}).sort("created_at", 1))
    if not include_internal:
        comments = [c for c in comments if not c.get("is_internal")]
    attachments = list(db.col("attachments").find({"incident_id": doc["_id"]}))
    if not participant:
        attachments = [a for a in attachments if not a.get("is_private")]
    escalations = list(db.col("escalations").find({"incident_id": doc["_id"]}).sort("created_at", 1))
    body = _enrich(db, doc, principal)
    body["history"] = [
        {
            "id": h["_id"],
            "from_status": h.get("from_status"),
            "to_status": h.get("to_status"),
            "note": h.get("note") if include_internal or h.get("to_status") else None,
            "created_at": dt(h.get("created_at")),
        }
        for h in history
    ]
    body["comments"] = serialize_comments(db, comments)
    body["viewer_has_promoted"] = user_has_promoted(db, doc["_id"], user["_id"])
    body["attachments"] = [attachment_public(a) for a in attachments]
    body["escalations"] = [
        {"id": e["_id"], "level": e.get("level"), "reason": e.get("reason"), "created_at": dt(e.get("created_at"))}
        for e in escalations
    ]
    return body


def _purge_incident(db: Database, incident_id: str) -> None:
    from app.services.storage import storage_service

    for att in db.col("attachments").find({"incident_id": incident_id}):
        key = att.get("storage_key") or att.get("object_key")
        if key:
            storage_service.delete(str(key))
    for name in (
        "attachments",
        "comments",
        "complaint_status_history",
        "assignments",
        "escalations",
        "reports",
        "votes",
        "notifications",
    ):
        db.col(name).delete_many({"incident_id": incident_id})
    db.col("complaints").delete_one({"_id": incident_id})


@router.delete("/api/complaints/{incident_id}")
def delete_complaint(incident_id: str, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    doc = db.col("complaints").find_one({"$or": [{"_id": incident_id}, {"reference": incident_id.upper()}]})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    if user.get("role") != "CITIZEN":
        raise AppError("Only citizens can delete their own reports this way.", 403, "FORBIDDEN")
    if doc.get("reporter_id") != user["_id"]:
        raise AppError("You can only delete reports you submitted.", 403, "FORBIDDEN")
    _purge_incident(db, doc["_id"])
    write_audit(
        db,
        action="incident.deleted",
        entity_type="complaint",
        actor_id=user["_id"],
        entity_id=doc["_id"],
        ip=None,
    )
    return Response(status_code=204)


@router.patch("/api/complaints/{incident_id}/status")
def update_status(incident_id: str, body: StatusUpdateIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    doc = db.col("complaints").find_one({"_id": incident_id})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    principal = principal_of(user)
    if not can_update_incident(principal, doc):
        raise AppError("You cannot update this incident", 403, "FORBIDDEN")
    try:
        assert_transition(doc["status"], body.status)
    except ValueError as exc:
        raise AppError(str(exc), 400, "INVALID_STATUS_TRANSITION") from exc
    now = now_utc()
    patch = {"status": body.status, "updated_at": now, "last_progress_at": now}
    if body.status == "RESOLVED":
        patch["resolved_at"] = now
    db.col("complaints").update_one({"_id": doc["_id"]}, {"$set": patch})
    db.col("complaint_status_history").insert_one(
        {
            "_id": uuid.uuid4().hex,
            "incident_id": doc["_id"],
            "from_status": doc["status"],
            "to_status": body.status,
            "note": body.note,
            "actor_id": user["_id"],
            "created_at": now,
        }
    )
    notify(
        db,
        user_id=doc["reporter_id"],
        ntype="STATUS_CHANGED",
        title="Status update",
        body=f"{doc.get('reference')} is now {body.status.replace('_', ' ').title()}.",
        incident_id=doc["_id"],
        dedupe_key=f"status:{doc['_id']}:{body.status}:{now.isoformat()}",
    )
    if body.status == "MORE_INFO_REQUESTED":
        notify(
            db,
            user_id=doc["reporter_id"],
            ntype="MORE_INFO_REQUESTED",
            title="More information requested",
            body=body.note or "An officer asked for more detail on your report.",
            incident_id=doc["_id"],
            dedupe_key=f"info:{doc['_id']}:{now.isoformat()}",
        )
    if body.status == "RESOLVED":
        notify(
            db,
            user_id=doc["reporter_id"],
            ntype="RESOLVED",
            title="Your report was marked resolved",
            body="Please review the resolution when you can.",
            incident_id=doc["_id"],
            dedupe_key=f"resolved:{doc['_id']}",
        )
    write_audit(db, action="incident.status", entity_type="complaint", actor_id=user["_id"], entity_id=doc["_id"], metadata={"to": body.status})
    pubsub_service.publish("incident.status_changed", {"incident_id": doc["_id"], "status": body.status})
    updated = db.col("complaints").find_one({"_id": doc["_id"]})
    _sync_bigquery(db, updated or doc)
    return _enrich(db, updated, principal)


@router.post("/api/complaints/{incident_id}/comments")
def add_comment(incident_id: str, body: CommentIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    doc = db.col("complaints").find_one({"_id": incident_id})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    principal = principal_of(user)
    if body.is_internal and not can_view_internal_notes(principal):
        raise AppError("Internal notes are limited to officers", 403, "FORBIDDEN")
    record = {
        "_id": uuid.uuid4().hex,
        "incident_id": doc["_id"],
        "author_id": user["_id"],
        "body": body.body.strip(),
        "is_internal": body.is_internal,
        "created_at": now_utc(),
    }
    db.col("comments").insert_one(record)
    db.col("complaints").update_one({"_id": doc["_id"]}, {"$set": {"last_progress_at": now_utc(), "updated_at": now_utc()}})
    if not body.is_internal and user["_id"] != doc["reporter_id"]:
        notify(
            db,
            user_id=doc["reporter_id"],
            ntype="COMMENT",
            title="New update on your report",
            body="There is a new public note on your incident.",
            incident_id=doc["_id"],
            dedupe_key=f"comment:{record['_id']}",
        )
    return {"id": record["_id"], "created_at": dt(record["created_at"])}


@router.post("/api/complaints/{incident_id}/assign")
def assign(incident_id: str, body: AssignIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    if user["role"] not in {"ADMIN", "OFFICER"}:
        raise AppError("You cannot assign incidents", 403, "FORBIDDEN")
    doc = db.col("complaints").find_one({"_id": incident_id})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    officer = db.col("users").find_one({"_id": body.officer_id, "role": {"$in": ["OFFICER", "ADMIN"]}, "is_active": True})
    if not officer:
        raise AppError("Officer not found", 400, "INVALID_OFFICER")
    now = now_utc()
    db.col("complaints").update_one(
        {"_id": doc["_id"]},
        {"$set": {"assigned_officer_id": officer["_id"], "updated_at": now, "last_progress_at": now}},
    )
    db.col("assignments").insert_one(
        {
            "_id": uuid.uuid4().hex,
            "incident_id": doc["_id"],
            "officer_id": officer["_id"],
            "assigned_by_id": user["_id"],
            "note": body.note,
            "unassigned_at": None,
            "created_at": now,
        }
    )
    if can_transition(doc["status"], "ACKNOWLEDGED") and doc["status"] == "SUBMITTED":
        db.col("complaints").update_one({"_id": doc["_id"]}, {"$set": {"status": "ACKNOWLEDGED"}})
        db.col("complaint_status_history").insert_one(
            {
                "_id": uuid.uuid4().hex,
                "incident_id": doc["_id"],
                "from_status": "SUBMITTED",
                "to_status": "ACKNOWLEDGED",
                "note": "Officer assigned",
                "actor_id": user["_id"],
                "created_at": now,
            }
        )
    notify(
        db,
        user_id=officer["_id"],
        ntype="ASSIGNED",
        title="Incident assigned to you",
        body=doc.get("reference") or doc.get("title"),
        incident_id=doc["_id"],
        dedupe_key=f"assign:{doc['_id']}:{officer['_id']}:{now.isoformat()}",
    )
    notify(
        db,
        user_id=doc["reporter_id"],
        ntype="ASSIGNED",
        title="An officer is reviewing your report",
        body=f"{doc.get('reference')} has been assigned.",
        incident_id=doc["_id"],
        dedupe_key=f"assign-reporter:{doc['_id']}:{now.isoformat()}",
    )
    write_audit(db, action="incident.assigned", entity_type="complaint", actor_id=user["_id"], entity_id=doc["_id"])
    return {"ok": True}


@router.post("/api/complaints/{incident_id}/escalate")
def escalate_manual(incident_id: str, body: EscalateIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    if user["role"] not in {"ADMIN", "OFFICER"}:
        raise AppError("You cannot escalate incidents", 403, "FORBIDDEN")
    doc = db.col("complaints").find_one({"_id": incident_id})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    existing = [int(e["level"]) for e in db.col("escalations").find({"incident_id": doc["_id"]})]
    level = (max(existing) + 1) if existing else 1
    if level > 3:
        raise AppError("This incident is already at the highest escalation level", 400, "MAX_ESCALATION")
    decision = EscalationDecision(
        incident_id=doc["_id"],
        level=level,
        reason=body.reason,
        idempotency_key=f"{doc['_id']}:level:{level}",
    )
    ok = apply_decision(db, decision, actor_id=user["_id"], triggered_by="manual")
    if not ok:
        raise AppError("This escalation was already recorded", 409, "DUPLICATE_ESCALATION")
    return {"ok": True, "level": level}


@router.post("/api/complaints/{incident_id}/attachments")
async def upload_attachment(
    incident_id: str,
    user: dict = Depends(current_user),
    db: Database = Depends(db_dep),
    file: UploadFile = File(...),
    kind: str = Query("report"),
    keep_private: bool = Query(False),
):
    doc = db.col("complaints").find_one({"_id": incident_id})
    if not doc:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    principal = principal_of(user)
    if not can_update_incident(principal, doc) and user["_id"] != doc.get("reporter_id"):
        raise AppError("You cannot attach files to this incident", 403, "FORBIDDEN")
    if kind not in {"report", "evidence", "internal"}:
        raise AppError("Invalid attachment kind", 400, "INVALID_KIND")
    if kind in {"evidence", "internal"} and user["role"] not in {"ADMIN", "OFFICER"}:
        raise AppError("Only officers can upload resolution evidence", 403, "FORBIDDEN")
    if kind == "report" and db.col("attachments").count_documents({"incident_id": doc["_id"], "kind": "report"}) >= MAX_REPORT_ATTACHMENTS:
        raise AppError(f"A report can include up to {MAX_REPORT_ATTACHMENTS} images.", 400, "TOO_MANY_FILES")
    data = await file.read(MAX_FILE_BYTES + 1)
    ok, ext_or_err = validate_upload(file.content_type or "", len(data), file.filename or "upload")
    if not ok:
        raise AppError(ext_or_err, 400, "INVALID_FILE")
    if len(data) > MAX_FILE_BYTES:
        raise AppError("Each photo must be 8 MB or smaller", 400, "FILE_TOO_LARGE")
    is_private = kind in {"internal", "evidence"} or (kind == "report" and keep_private)
    key = storage_service.save(data, file.content_type or "application/octet-stream", file.filename or "upload", f"complaints/{kind}")
    att = {
        "_id": uuid.uuid4().hex,
        "incident_id": doc["_id"],
        "kind": kind,
        "object_key": key,
        "original_name": file.filename or "upload",
        "mime_type": file.content_type,
        "size_bytes": len(data),
        "is_private": is_private,
        "uploaded_by_id": user["_id"],
        "created_at": now_utc(),
    }
    db.col("attachments").insert_one(att)
    db.col("complaints").update_one({"_id": doc["_id"]}, {"$set": {"last_progress_at": now_utc(), "updated_at": now_utc()}})
    write_audit(db, action="incident.attachment", entity_type="attachment", actor_id=user["_id"], entity_id=att["_id"])
    return attachment_public(att)


@router.get("/api/attachments/{attachment_id}")
def get_attachment(attachment_id: str, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    att = db.col("attachments").find_one({"_id": attachment_id})
    if not att:
        raise AppError("Attachment not found", 404, "NOT_FOUND")
    incident = db.col("complaints").find_one({"_id": att["incident_id"]})
    if not incident:
        raise AppError("Attachment not found", 404, "NOT_FOUND")
    if att.get("is_private") and not can_view_report_sensitive(principal_of(user), incident):
        raise AppError("Attachment not found", 404, "NOT_FOUND")
    data = storage_service.load(att["object_key"])
    return Response(content=data, media_type=att.get("mime_type") or "application/octet-stream")
