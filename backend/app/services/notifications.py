from __future__ import annotations

import logging
import uuid

from app.db import Database, DuplicateKeyError
from app.security import now_utc

log = logging.getLogger("civicon.notifications")


def notify(
    db: Database,
    *,
    user_id: str,
    ntype: str,
    title: str,
    body: str,
    incident_id: str | None = None,
    dedupe_key: str,
) -> bool:
    moment = now_utc()
    if incident_id:
        existing = db.col("notifications").find_one({"user_id": user_id, "incident_id": incident_id})
        if existing:
            db.col("notifications").update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "type": ntype,
                        "title": title,
                        "body": body,
                        "dedupe_key": dedupe_key,
                        "read_at": None,
                        "updated_at": moment,
                    }
                },
            )
            return True
    try:
        db.col("notifications").insert_one(
            {
                "_id": uuid.uuid4().hex,
                "user_id": user_id,
                "type": ntype,
                "title": title,
                "body": body,
                "incident_id": incident_id,
                "dedupe_key": dedupe_key,
                "read_at": None,
                "email_status": None,
                "fcm_status": None,
                "created_at": moment,
                "updated_at": moment,
            }
        )
        return True
    except DuplicateKeyError:
        return False
    except Exception as exc:
        if "duplicate" in str(exc).lower():
            return False
        log.warning("notification_insert_failed type=%s", type(exc).__name__)
        return False
