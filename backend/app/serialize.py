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


def complaint_public(doc: dict, *, include_internal: bool = False, extras: dict | None = None) -> dict:
    body = {
        "id": doc["_id"],
        "reference": doc.get("reference"),
        "title": doc.get("title"),
        "description": doc.get("description") if include_internal else _public_description(doc),
        "summary": doc.get("summary"),
        "category_id": doc.get("category_id"),
        "department_id": doc.get("department_id"),
        "status": doc.get("status"),
        "severity": doc.get("severity"),
        "locality": doc.get("locality"),
        "latitude": doc.get("latitude"),
        "longitude": doc.get("longitude"),
        "occurred_at": dt(doc.get("occurred_at")),
        "is_public": doc.get("is_public", True),
        "created_at": dt(doc.get("created_at")),
        "updated_at": dt(doc.get("updated_at")),
        "resolved_at": dt(doc.get("resolved_at")),
        "last_progress_at": dt(doc.get("last_progress_at")),
        "source": doc.get("source") or "user",
        "escalation_level": doc.get("escalation_level") or 1,
        "escalated_by_threshold": bool(doc.get("escalated_by_threshold")),
        "human_review_required": bool(doc.get("human_review_required")),
        "priority": doc.get("priority"),
        "counters": doc.get("counters") or {},
        "claimed_by": doc.get("claimed_by"),
        "sla": {
            "ack_due": dt((doc.get("sla") or {}).get("ack_due")) if isinstance(doc.get("sla"), dict) else None,
            "resolve_due": dt((doc.get("sla") or {}).get("resolve_due")) if isinstance(doc.get("sla"), dict) else None,
        },
        "lifecycle": (doc.get("status") or "").lower() if str(doc.get("status", "")).islower() else None,
    }
    if include_internal:
        body.update(
            {
                "address": doc.get("address"),
                "reporter_id": doc.get("reporter_id"),
                "assigned_officer_id": doc.get("assigned_officer_id"),
                "duplicate_of_id": doc.get("duplicate_of_id"),
                "ai_category_slug": doc.get("ai_category_slug"),
                "ai_severity": doc.get("ai_severity"),
                "ai_department_code": doc.get("ai_department_code"),
                "ai_rationale": doc.get("ai_rationale"),
                "ai_generated": True if doc.get("ai_rationale") else False,
            }
        )
    if extras:
        body.update(extras)
    return body


def _public_description(doc: dict) -> str:
    text = doc.get("summary") or doc.get("description") or ""
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
