from __future__ import annotations

import json
import uuid
from typing import Any

from app.db import Database
from app.security import now_utc


def write_audit(
    db: Database,
    *,
    action: str,
    entity_type: str,
    actor_id: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip: str | None = None,
    request_id: str | None = None,
) -> None:
    safe_meta = metadata or {}
    for key in list(safe_meta.keys()):
        if any(part in key.lower() for part in ("password", "token", "secret", "key", "credential")):
            safe_meta[key] = "[redacted]"
    db.col("audit_logs").insert_one(
        {
            "_id": uuid.uuid4().hex,
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": json.dumps(safe_meta),
            "ip": ip,
            "request_id": request_id,
            "created_at": now_utc(),
        }
    )
