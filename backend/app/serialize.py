from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db import iso


def user_public(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "email": doc["email"],
        "display_name": doc.get("display_name"),
        "phone": doc.get("phone"),
        "role": doc.get("role"),
        "department_id": doc.get("department_id"),
        "locality": doc.get("locality"),
        "date_of_birth": doc.get("date_of_birth"),
        "is_active": doc.get("is_active", True),
        "region_id": doc.get("region_id"),
        "authority_level": doc.get("authority_level"),
        "bootstrap_account": doc.get("bootstrap_account", False),
        "demo_account": doc.get("bootstrap_account", doc.get("demo_account", False)),
    }


def dt(value: Any) -> str | None:
    if isinstance(value, datetime):
        return iso(value)
    if value is None:
        return None
    return str(value)


def complaint_public(
    doc: dict,
    *,
    signed_in: bool = False,
    include_internal: bool = False,
    extras: dict | None = None,
) -> dict:
    body = {
        "id": doc["_id"],
        "reference": doc.get("reference"),
        "title": doc.get("title"),
        "locality": doc.get("locality"),
        "latitude": doc.get("latitude"),
        "longitude": doc.get("longitude"),
        "counters": {"promotes": (doc.get("counters") or {}).get("promotes", 0)},
    }
    if signed_in:
        body.update(
            {
                "summary": _public_description(doc),
                "description": _public_description(doc),
                "category_id": doc.get("category_id"),
                "department_id": doc.get("department_id"),
                "status": doc.get("status"),
                "created_at": dt(doc.get("created_at")),
                "updated_at": dt(doc.get("updated_at")),
                "resolved_at": dt(doc.get("resolved_at")),
                "last_progress_at": dt(doc.get("last_progress_at")),
                "priority": doc.get("priority"),
                "counters": doc.get("counters") or {},
            }
        )
    if include_internal:
        body.update(
            {
                "description": doc.get("description"),
                "address": doc.get("address"),
                "reporter_id": doc.get("reporter_id"),
                "assigned_officer_id": doc.get("assigned_officer_id"),
                "duplicate_of_id": doc.get("duplicate_of_id"),
                "occurred_at": dt(doc.get("occurred_at")),
                "severity": doc.get("severity"),
                "ai_summary": doc.get("ai_summary"),
                "attachment_inference": doc.get("attachment_inference"),
                "ai_category_slug": doc.get("ai_category_slug"),
                "ai_severity": doc.get("ai_severity"),
                "ai_department_code": doc.get("ai_department_code"),
                "ai_rationale": doc.get("ai_rationale"),
                "ai_generated": True if doc.get("ai_rationale") else False,
                "source": doc.get("source") or "user",
                "escalation_level": doc.get("escalation_level") or 1,
                "escalated_by_threshold": bool(doc.get("escalated_by_threshold")),
                "human_review_required": bool(doc.get("human_review_required")),
                "claimed_by": doc.get("claimed_by"),
                "sla": {
                    "ack_due": dt((doc.get("sla") or {}).get("ack_due"))
                    if isinstance(doc.get("sla"), dict)
                    else None,
                    "resolve_due": dt((doc.get("sla") or {}).get("resolve_due"))
                    if isinstance(doc.get("sla"), dict)
                    else None,
                },
            }
        )
    if extras:
        body.update(extras)
    return body


def _public_description(doc: dict) -> str:
    text = doc.get("description") or doc.get("title") or ""
    return text[:280]


def attachment_public(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "kind": doc.get("kind"),
        "original_name": doc.get("original_name"),
        "mime_type": doc.get("mime_type"),
        "size_bytes": doc.get("size_bytes"),
        "is_private": doc.get("is_private", True),
        "created_at": dt(doc.get("created_at")),
    }


def serialize_comments(db, comments: list[dict]) -> list[dict]:
    author_ids = [c.get("author_id") for c in comments if c.get("author_id")]
    users_by_id: dict[str, dict] = {}
    if author_ids:
        for user in db.col("users").find({"_id": {"$in": author_ids}}):
            users_by_id[user["_id"]] = user
    rows: list[dict] = []
    for comment in comments:
        author_id = comment.get("author_id")
        author = users_by_id.get(author_id) or {}
        rows.append(
            {
                "id": comment["_id"],
                "body": comment["body"],
                "is_internal": comment.get("is_internal", False),
                "author_id": author_id,
                "author": {
                    "id": author_id,
                    "display_name": author.get("display_name") or "Community member",
                },
                "created_at": dt(comment.get("created_at")),
            }
        )
    return rows


def user_has_promoted(db, incident_id: str, user_id: str | None) -> bool:
    if not user_id:
        return False
    return bool(
        db.col("votes").find_one({"incident_id": incident_id, "uid": user_id, "type": "promote"})
    )
