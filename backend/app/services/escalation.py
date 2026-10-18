from __future__ import annotations

import uuid
from datetime import datetime

from app.config import get_settings
from app.db import Database, DuplicateKeyError
from app.domain.escalation import EscalationCandidate, EscalationRule, evaluate_batch
from app.domain.status import can_transition, is_open_status
from app.security import now_utc
from app.services.audit import write_audit
from app.services.notifications import notify
from app.services.pubsub import pubsub_service


def _as_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return now_utc()


def run_escalations(db: Database, actor_id: str | None = None, triggered_by: str = "scheduler") -> dict:
    settings = get_settings()
    now = now_utc()
    rules = [
        EscalationRule(
            id=r["_id"],
            category_id=r.get("category_id"),
            severity=r.get("severity"),
            level=int(r.get("level") or 1),
            review_hours=int(r.get("review_hours") or 24),
            resolve_hours=int(r.get("resolve_hours") or 168),
            reason=r.get("reason") or "SLA",
            is_active=bool(r.get("is_active", True)),
        )
        for r in db.col("escalation_rules").find({"is_active": True})
    ]
    open_incidents = [
        d
        for d in db.col("complaints").find({})
        if is_open_status(d.get("status", "SUBMITTED"))
    ]
    candidates: list[EscalationCandidate] = []
    for inc in open_incidents:
        existing = [
            int(e["level"])
            for e in db.col("escalations").find({"incident_id": inc["_id"]})
        ]
        existing.sort()
        candidates.append(
            EscalationCandidate(
                id=inc["_id"],
                category_id=inc.get("category_id") or "",
                status=inc.get("status"),
                severity=inc.get("severity") or "MEDIUM",
                assigned_officer_id=inc.get("assigned_officer_id"),
                created_at=_as_dt(inc.get("created_at")),
                last_progress_at=_as_dt(inc.get("last_progress_at") or inc.get("created_at")),
                existing_levels=existing,
            )
        )
    decisions = evaluate_batch(candidates, rules, now, settings.demo_time_scale)
    applied = 0
    skipped = 0
    for decision in decisions:
        ok = apply_decision(db, decision, actor_id=actor_id, triggered_by=triggered_by)
        if ok:
            applied += 1
        else:
            skipped += 1
    return {"evaluated": len(candidates), "decisions": len(decisions), "applied": applied, "skipped": skipped}


def apply_decision(db: Database, decision, actor_id: str | None, triggered_by: str) -> bool:
    incident = db.col("complaints").find_one({"_id": decision.incident_id})
    if not incident:
        return False
    record = {
        "_id": uuid.uuid4().hex,
        "incident_id": decision.incident_id,
        "level": decision.level,
        "reason": decision.reason,
        "triggered_by": triggered_by,
        "actor_id": actor_id,
        "idempotency_key": decision.idempotency_key,
        "created_at": now_utc(),
    }
    try:
        db.col("escalations").insert_one(record)
    except DuplicateKeyError:
        return False
    except Exception as exc:
        if "duplicate" in str(exc).lower():
            return False
        raise
    from_status = incident.get("status")
    now = now_utc()
    patch = {"last_progress_at": now, "updated_at": now}
    moved = can_transition(from_status, "ESCALATED")
    if moved:
        patch["status"] = "ESCALATED"
    db.col("complaints").update_one({"_id": incident["_id"]}, {"$set": patch})
    if moved:
        db.col("complaint_status_history").insert_one(
            {
                "_id": uuid.uuid4().hex,
                "incident_id": incident["_id"],
                "from_status": from_status,
                "to_status": "ESCALATED",
                "note": decision.reason,
                "actor_id": actor_id,
                "created_at": now_utc(),
            }
        )
    notify(
        db,
        user_id=incident["reporter_id"],
        ntype="ESCALATED",
        title="Your report was escalated",
        body=f"{incident.get('reference')} moved to an escalation review.",
        incident_id=incident["_id"],
        dedupe_key=f"esc:{decision.idempotency_key}:reporter",
    )
    if incident.get("assigned_officer_id"):
        notify(
            db,
            user_id=incident["assigned_officer_id"],
            ntype="ESCALATED",
            title="Incident escalated",
            body=decision.reason,
            incident_id=incident["_id"],
            dedupe_key=f"esc:{decision.idempotency_key}:officer",
        )
    write_audit(
        db,
        action="incident.escalated",
        entity_type="complaint",
        actor_id=actor_id,
        entity_id=incident["_id"],
        metadata={"level": decision.level, "triggered_by": triggered_by},
    )
    pubsub_service.publish(
        "incident.escalated",
        {"incident_id": incident["_id"], "reference": incident.get("reference"), "level": decision.level},
    )
    return True
