from __future__ import annotations

import base64
import json
import uuid

from fastapi import APIRouter, Depends

from app.db import Database
from app.deps import db_dep, require_internal
from app.security import now_utc
from app.services.escalation import run_escalations

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tasks/escalate")
def escalate_job(_: bool = Depends(require_internal), db: Database = Depends(db_dep)):
    from app.services.priority import run_sla_tick

    legacy = run_escalations(db, triggered_by="scheduler")
    sla = run_sla_tick(db)
    return {"legacy": legacy, "sla": sla}


@router.post("/tick/sla")
def sla_tick(_: bool = Depends(require_internal), db: Database = Depends(db_dep)):
    from app.services.priority import run_sla_tick

    return run_sla_tick(db)


@router.post("/tick/weather")
def weather_tick(_: bool = Depends(require_internal), db: Database = Depends(db_dep)):
    from app.services.weather import run_weather_tick

    return run_weather_tick(db)


@router.post("/events")
def pubsub_push(body: dict, _: bool = Depends(require_internal), db: Database = Depends(db_dep)):
    message = body.get("message") or {}
    message_id = message.get("messageId") or message.get("message_id") or uuid.uuid4().hex
    if db.col("processed_events").find_one({"_id": message_id}):
        return {"ok": True, "duplicate": True}
    payload: dict = {}
    data = message.get("data")
    if isinstance(data, str) and data:
        try:
            payload = json.loads(base64.b64decode(data).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            payload = {"raw": True}
    db.col("processed_events").insert_one(
        {
            "_id": message_id,
            "event_type": payload.get("type") or (message.get("attributes") or {}).get("event_type"),
            "payload": payload,
            "created_at": now_utc(),
        }
    )
    event_type = payload.get("type")
    if event_type == "incident.escalation_check":
        return run_escalations(db, triggered_by="pubsub")
    return {"ok": True, "duplicate": False}
