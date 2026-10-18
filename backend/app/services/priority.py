from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db import Database
from app.domain.geo import distance_m
from app.domain.lifecycle import CATEGORY_GROUP, GROUP_RADIUS_M, canonical, is_open_lifecycle
from app.domain.scoring import (
    SLA_MINUTES,
    category_base_severity,
    community_factor,
    deadlines_for,
    label_for,
    life_safety,
    priority_score,
    urgency_factor,
)
from app.security import now_utc
from app.services.notifications import notify

CLUSTER_WINDOW = timedelta(hours=24)


def score_incident(db: Database, incident_id: str, *, now: datetime | None = None) -> dict | None:
    moment = now or now_utc()
    incident = db.col("complaints").find_one({"_id": incident_id})
    if not incident:
        return None
    if not is_open_lifecycle(incident.get("status", "")):
        return incident.get("priority")
    reporters = cluster_reporter_ids(db, incident, moment)
    own = reporters_for(db, [incident_id], moment - CLUSTER_WINDOW)
    counters = dict(incident.get("counters") or {})
    ai_doc = incident.get("ai") if isinstance(incident.get("ai"), dict) else {}
    ai = incident.get("ai_severity_0_1")
    if ai is None:
        ai = (ai_doc or {}).get("severity_0_1")
    if ai is None:
        slug = (incident.get("ai_category_slug") or "") or ""
        cat = db.col("categories").find_one({"_id": incident.get("category_id")}) or {}
        slug = slug or cat.get("slug") or "other"
        ai = category_base_severity(slug)
    corroboration = min(1.0, len(reporters) / 5)
    community = community_factor(int(counters.get("promotes") or 0), int(counters.get("better") or 0))
    exposure = 0.0
    weather = float(incident.get("weather_multiplier") or 1)
    if int(counters.get("better") or 0) > 0:
        weather = weather / (1 + int(counters["better"]))
    urgency = urgency_factor(moment - _aware(incident.get("created_at") or moment), timedelta(minutes=SLA_MINUTES["Medium"]["ack"]), weather)
    score, factors = priority_score(
        ai=float(ai),
        corroboration=corroboration,
        community=community,
        exposure=exposure,
        urgency=urgency,
        reporters=len(reporters),
    )
    review = bool(incident.get("human_review_required")) or life_safety(_slug(db, incident), ai_doc)
    threshold = len(reporters) >= 5
    if threshold and score < 65:
        score = 65
        factors.append({"name": "Local threshold", "value": 1, "detail": f"{len(reporters)} unique reporters in 24h"})
    label = label_for(score)
    priority = {"score": score, "label": label, "factors": factors}
    counters["unique_reporters"] = len(own)
    already_threshold = bool(incident.get("escalated_by_threshold"))
    db.col("complaints").update_one(
        {"_id": incident_id},
        {
            "$set": {
                "priority": priority,
                "sla": deadlines_for(label, _aware(incident.get("created_at") or moment)),
                "counters": counters,
                "human_review_required": review,
                "escalated_by_threshold": threshold,
                "updated_at": moment,
            }
        },
    )
    if threshold and not already_threshold:
        _fanout(db, incident, "R1", "5 people reported this.", moment)
    if review and not incident.get("human_review_required"):
        _fanout(db, incident, "R2", "This may be a safety risk.", moment)
    return priority


def cluster_reporter_ids(db: Database, incident: dict, now: datetime) -> set[str]:
    since = now - CLUSTER_WINDOW
    members = [m for m, _ in cluster_members(db, incident, since)]
    if incident["_id"] not in members:
        members.append(incident["_id"])
    return reporters_for(db, members, since)


def reporters_for(db: Database, incident_ids: list[str], since: datetime) -> set[str]:
    found: set[str] = set()
    for iid in incident_ids:
        for report in db.col("reports").find({"incident_id": iid}):
            created = report.get("created_at")
            uid = report.get("uid")
            if uid and created and _aware(created) >= since:
                found.add(uid)
    return found


def cluster_members(db: Database, incident: dict, since: datetime) -> list[tuple[str, dict]]:
    slug = _slug(db, incident)
    group = CATEGORY_GROUP.get(slug)
    if group is None:
        return []
    radius = GROUP_RADIUS_M[group]
    lat, lng = incident.get("latitude"), incident.get("longitude")
    if lat is None or lng is None:
        return []
    out: list[tuple[str, dict]] = []
    for other in db.col("complaints").find({}):
        if canonical(other.get("status", "")) not in {"reported", "triaged", "assigned", "in_progress", "reopened"}:
            continue
        if _aware(other.get("created_at") or since) < since:
            continue
        if CATEGORY_GROUP.get(_slug(db, other)) != group:
            continue
        if other.get("latitude") is None:
            continue
        if distance_m(lat, lng, other["latitude"], other["longitude"]) <= radius:
            out.append((other["_id"], other))
    return out


def merge_into_nearby(db: Database, incident: dict) -> str | None:
    """If a nearby open incident in the same group exists, attach this report instead."""
    now = now_utc()
    members = cluster_members(db, incident, now - CLUSTER_WINDOW)
    for other_id, other in members:
        if other_id != incident["_id"]:
            return other_id
    return None


def run_sla_tick(db: Database, *, now: datetime | None = None) -> dict:
    from app.services.community import review_verifications

    moment = now or now_utc()
    moved = 0
    skipped = 0
    for incident in db.col("complaints").find({}):
        if escalate_sla(db, incident, moment):
            moved += 1
        else:
            skipped += 1
    closed = review_verifications(db, now=moment)
    return {"evaluated": moved + skipped, "applied": moved, "verification_closed": closed}


def escalate_sla(db: Database, incident: dict, moment: datetime) -> bool:
    if int(incident.get("escalation_level") or 1) >= 3:
        return False
    if canonical(incident.get("status", "")) in {"resolved_pending_verification", "closed", "closed_unverified"}:
        return False
    reason = _sla_reason(incident, moment)
    if not reason:
        return False
    level = int(incident.get("escalation_level") or 1) + 1
    key = f"{incident['_id']}:sla:{level}"
    if db.col("escalations").find_one({"idempotency_key": key}):
        return False
    db.col("escalations").insert_one(
        {
            "_id": key,
            "incident_id": incident["_id"],
            "level": level,
            "reason": reason,
            "triggered_by": "sla",
            "idempotency_key": key,
            "created_at": moment,
        }
    )
    db.col("complaints").update_one(
        {"_id": incident["_id"]},
        {"$set": {"escalation_level": level, "updated_at": moment, "last_progress_at": moment}},
    )
    db.col("complaint_status_history").insert_one(
        {
            "_id": f"tl-{key}",
            "incident_id": incident["_id"],
            "from_status": incident.get("status"),
            "to_status": incident.get("status"),
            "note": reason,
            "actor_id": None,
            "created_at": moment,
        }
    )
    _fanout(db, incident, "ESCALATED", "Moved to the next level.", moment)
    return True


def _sla_reason(incident: dict, now: datetime) -> str | None:
    sla = incident.get("sla") or {}
    status = canonical(incident.get("status", ""))
    level = int(incident.get("escalation_level") or 1)
    ack = sla.get("ack_due")
    resolve = sla.get("resolve_due")
    if level == 1 and ack and now >= _aware(ack) and status in {"reported", "SUBMITTED"}:
        return "The acknowledge deadline passed."
    label = (incident.get("priority") or {}).get("label") or "Medium"
    l3_min = SLA_MINUTES.get(label, {}).get("l3")
    created = _aware(incident.get("created_at") or now)
    if level == 2 and l3_min and now >= created + timedelta(minutes=l3_min):
        return "The level 3 deadline passed."
    if resolve and now >= _aware(resolve) and status not in {"resolved_pending_verification", "closed", "closed_unverified"}:
        return "The resolve deadline passed."
    return None


def add_report(db: Database, incident_id: str, uid: str, text: str, now: datetime | None = None) -> None:
    moment = now or now_utc()
    db.col("reports").insert_one(
        {
            "_id": f"{incident_id}:{uid}:{moment.timestamp()}",
            "incident_id": incident_id,
            "uid": uid,
            "text": text,
            "created_at": moment,
        }
    )


def _slug(db: Database, incident: dict) -> str:
    if incident.get("ai_category_slug"):
        return incident["ai_category_slug"]
    cat = db.col("categories").find_one({"_id": incident.get("category_id")}) or {}
    return cat.get("slug") or "other"


def _fanout(db: Database, incident: dict, ntype: str, body: str, now: datetime) -> None:
    uid = incident.get("reporter_id")
    if uid:
        notify(
            db,
            user_id=uid,
            ntype=ntype,
            title=incident.get("title") or "Incident update",
            body=body,
            incident_id=incident["_id"],
            dedupe_key=f"{ntype}:{incident['_id']}:{uid}",
        )


def _aware(value) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return now_utc()
