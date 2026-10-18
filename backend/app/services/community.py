from __future__ import annotations

from datetime import datetime, timedelta

from app.db import Database, DuplicateKeyError
from app.domain.lifecycle import canonical
from app.errors import AppError
from app.security import now_utc
from app.services.notifications import notify
from app.services.priority import score_incident

VERIFY_MAP = {"resolved": "resolved_yes", "unresolved": "resolved_no"}


def promote(db: Database, incident_id: str, user_id: str) -> dict:
    incident = _need(db, incident_id)
    counted = _cast(db, incident_id, user_id, "promote")
    total = _bump(db, incident_id, "promotes", counted)
    return {"counted": counted, "total": total, "reference": incident.get("reference")}


def currently_better(db: Database, incident_id: str, user_id: str) -> dict:
    incident = _need(db, incident_id)
    if incident.get("source") != "auto_weather":
        raise AppError("Currently better is only for weather posts", 400, "INVALID")
    counted = _cast(db, incident_id, user_id, "better")
    total = _bump(db, incident_id, "better", counted)
    if counted:
        score_incident(db, incident_id)
    return {"counted": counted, "total": total}


def verify(db: Database, incident_id: str, user_id: str, answer: str) -> dict:
    incident = _need(db, incident_id)
    if canonical(incident.get("status", "")) != "resolved_pending_verification":
        raise AppError("Verification is not open", 400, "INVALID")
    if user_id not in follower_ids(db, incident_id):
        raise AppError("Only reporters and promoters can answer", 403, "FORBIDDEN")
    vote_type = VERIFY_MAP.get(answer)
    if not vote_type:
        raise AppError("Answer resolved or unresolved", 400, "INVALID")
    field = "yes" if vote_type == "resolved_yes" else "no"
    if _has_verify(db, incident_id, user_id):
        return {"counted": False, "total": _count(db, incident_id, field)}
    counted = _cast(db, incident_id, user_id, vote_type)
    total = _bump(db, incident_id, field, counted)
    if counted:
        _settle(db, incident_id)
    return {"counted": counted, "total": total}


def apply_r4(db: Database, incident_id: str, now: datetime | None = None) -> bool:
    moment = now or now_utc()
    incident = db.col("complaints").find_one({"_id": incident_id})
    if not incident:
        return False
    if canonical(incident.get("status", "")) not in {"resolved_pending_verification", "closed"}:
        return False
    no_voters = {v["uid"] for v in db.col("votes").find({"incident_id": incident_id, "type": "resolved_no"})}
    if len(no_voters) < 2:
        return False
    level = min(3, int(incident.get("escalation_level") or 1) + 1)
    db.col("complaints").update_one(
        {"_id": incident_id},
        {"$set": {"status": "reopened", "escalation_level": level, "updated_at": moment, "last_progress_at": moment}},
    )
    db.col("complaint_status_history").insert_one(
        {
            "_id": f"r4-{incident_id}-{level}",
            "incident_id": incident_id,
            "from_status": incident.get("status"),
            "to_status": "reopened",
            "note": "Reopened after two still-unresolved votes.",
            "actor_id": None,
            "created_at": moment,
        }
    )
    if incident.get("reporter_id"):
        notify(
            db,
            user_id=incident["reporter_id"],
            ntype="REOPENED",
            title="Still a problem",
            body="Reopened after two still-unresolved votes.",
            incident_id=incident_id,
            dedupe_key=f"r4:{incident_id}",
        )
    return True


def review_verifications(db: Database, *, now: datetime | None = None) -> int:
    from app.config import get_settings

    moment = now or now_utc()
    scale = get_settings().demo_time_scale if get_settings().demo_time_scale > 0 else 1
    window = timedelta(hours=48) / scale
    closed = 0
    for incident in db.col("complaints").find({"status": {"$in": ["resolved_pending_verification", "RESOLVED"]}}):
        if list(db.col("votes").find({"incident_id": incident["_id"], "type": "resolved_no"})):
            continue
        entered = None
        for row in db.col("complaint_status_history").find({"incident_id": incident["_id"]}):
            if canonical(row.get("to_status") or "") == "resolved_pending_verification" or row.get("to_status") == "RESOLVED":
                entered = row.get("created_at")
        if entered is None or moment - entered < window:
            continue
        db.col("complaints").update_one(
            {"_id": incident["_id"]},
            {"$set": {"status": "closed_unverified", "updated_at": moment}},
        )
        closed += 1
    return closed


def follower_ids(db: Database, incident_id: str) -> set[str]:
    found: set[str] = set()
    incident = db.col("complaints").find_one({"_id": incident_id}) or {}
    if incident.get("reporter_id"):
        found.add(incident["reporter_id"])
    for report in db.col("reports").find({"incident_id": incident_id}):
        if report.get("uid"):
            found.add(report["uid"])
    for vote in db.col("votes").find({"incident_id": incident_id, "type": "promote"}):
        if vote.get("uid"):
            found.add(vote["uid"])
    return found


def claim(db: Database, incident_id: str, user_id: str) -> dict:
    incident = _need(db, incident_id)
    db.col("complaints").update_one(
        {"_id": incident_id},
        {
            "$set": {
                "claimed_by": user_id,
                "assigned_officer_id": user_id,
                "status": (
                    "ACKNOWLEDGED"
                    if canonical(incident.get("status", "")) in {"reported", "triaged"}
                    else incident.get("status")
                ),
                "updated_at": now_utc(),
                "last_progress_at": now_utc(),
            }
        },
    )
    return {"ok": True}


def _settle(db: Database, incident_id: str) -> None:
    yes = {v["uid"] for v in db.col("votes").find({"incident_id": incident_id, "type": "resolved_yes"})}
    no = {v["uid"] for v in db.col("votes").find({"incident_id": incident_id, "type": "resolved_no"})}
    if len(no) >= 2:
        apply_r4(db, incident_id)
        return
    total = len(yes) + len(no)
    if len(yes) >= 2 and total and len(yes) / total >= 0.6:
        db.col("complaints").update_one({"_id": incident_id}, {"$set": {"status": "closed", "updated_at": now_utc()}})


def _cast(db: Database, incident_id: str, user_id: str, vote_type: str) -> bool:
    key = f"{incident_id}:{user_id}:{vote_type}"
    try:
        db.col("votes").insert_one(
            {
                "_id": key,
                "vote_key": key,
                "incident_id": incident_id,
                "uid": user_id,
                "type": vote_type,
                "created_at": now_utc(),
            }
        )
        return True
    except DuplicateKeyError:
        return False
    except Exception as exc:
        if "duplicate" in str(exc).lower():
            return False
        raise


def _bump(db: Database, incident_id: str, field: str, counted: bool) -> int:
    incident = db.col("complaints").find_one({"_id": incident_id}) or {}
    counters = dict(incident.get("counters") or {})
    if counted:
        counters[field] = int(counters.get(field) or 0) + 1
        db.col("complaints").update_one({"_id": incident_id}, {"$set": {"counters": counters, "updated_at": now_utc()}})
    return int(counters.get(field) or 0)


def _count(db: Database, incident_id: str, field: str) -> int:
    incident = db.col("complaints").find_one({"_id": incident_id}) or {}
    return int((incident.get("counters") or {}).get(field) or 0)


def _has_verify(db: Database, incident_id: str, user_id: str) -> bool:
    return bool(
        db.col("votes").find_one(
            {"incident_id": incident_id, "uid": user_id, "type": {"$in": ["resolved_yes", "resolved_no"]}}
        )
    )


def _need(db: Database, incident_id: str) -> dict:
    incident = db.col("complaints").find_one({"$or": [{"_id": incident_id}, {"reference": incident_id.upper()}]})
    if not incident:
        raise AppError("Incident not found", 404, "NOT_FOUND")
    return incident
