from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.config import get_settings
from app.services.weather_client import fetch_forecast
from app.db import Database
from app.domain.geo import distance_m, encode_geohash
from app.domain.lifecycle import canonical
from app.security import now_utc
from app.services.priority import score_incident

log = logging.getLogger("civicon.weather")
RAIN_SUM_MM = 10.0
RAIN_HOUR_MM = 7.6
HEAT_C = 40.0
FUSE_RADIUS_M = 500
FUSE_CATEGORIES = {"drainage", "water", "electrical", "streetlights"}


def run_weather_tick(db: Database, *, now: datetime | None = None, forecast: dict | None = None) -> dict:
    moment = now or now_utc()
    created = 0
    fused = 0
    points = _points(db)
    for lat, lng in points:
        payload = forecast or _fetch(lat, lng)
        kind = classify(payload, moment)
        if not kind:
            continue
        if not _existing_post(db, kind, lat, lng):
            _create_post(db, kind, lat, lng, moment)
            created += 1
        fused += _fuse(db, lat, lng, moment)
    return {"created": created, "fused": fused, "points": len(points)}


def classify(payload: dict, now: datetime) -> str | None:
    hourly = payload.get("hourly") or {}
    temps = hourly.get("temperature_2m") or []
    rain = hourly.get("precipitation") or hourly.get("rain") or []
    if rain and (sum(float(x or 0) for x in rain[:6]) >= RAIN_SUM_MM or any(float(x or 0) >= RAIN_HOUR_MM for x in rain[:6])):
        return "rain"
    if temps and any(float(x or 0) >= HEAT_C for x in temps[:6]):
        return "heat"
    current = payload.get("current") or {}
    if float(current.get("precipitation") or 0) >= RAIN_HOUR_MM:
        return "rain"
    return None


def _fetch(lat: float, lng: float) -> dict:
    return fetch_forecast(lat, lng)


def _points(db: Database) -> list[tuple[float, float]]:
    found: list[tuple[float, float]] = []
    for loc in db.col("saved_locations").find({}):
        if loc.get("lat") is not None:
            found.append((loc["lat"], loc["lng"]))
    for incident in db.col("complaints").find({}):
        if incident.get("latitude") is not None:
            found.append((incident["latitude"], incident["longitude"]))
    if not found:
        settings = get_settings()
        center = settings.map_center
        if center:
            found.append(center)
        else:
            from app.services.regions import municipality_region

            muni = municipality_region(db)
            if muni and muni.get("latitude") is not None:
                found.append((float(muni["latitude"]), float(muni["longitude"])))
    # de-dupe roughly
    uniq = []
    for lat, lng in found:
        if not any(distance_m(lat, lng, a, b) < 800 for a, b in uniq):
            uniq.append((lat, lng))
    return uniq[:12]


def _existing_post(db: Database, kind: str, lat: float, lng: float):
    for doc in db.col("complaints").find({"source": "auto_weather"}):
        if doc.get("weather_kind") == kind and doc.get("latitude") is not None:
            if distance_m(lat, lng, doc["latitude"], doc["longitude"]) < 1000:
                return doc
    return None


def _create_post(db: Database, kind: str, lat: float, lng: float, now: datetime) -> str:
    cid = uuid4().hex
    title = "Heavy rain expected" if kind == "rain" else "High heat expected"
    cat = db.col("categories").find_one({"slug": "drainage"}) or db.col("categories").find_one({})
    db.col("complaints").insert_one(
        {
            "_id": cid,
            "reference": f"WX-{now.year}-{cid[:6].upper()}",
            "title": title,
            "description": "Automatic weather post. Promote or mark currently better.",
            "summary": title,
            "category_id": cat["_id"] if cat else None,
            "status": "reported",
            "severity": "HIGH" if kind == "rain" else "MEDIUM",
            "source": "auto_weather",
            "weather_kind": kind,
            "locality": "Watched area",
            "latitude": lat,
            "longitude": lng,
            "geohash": encode_geohash(lat, lng),
            "is_public": True,
            "reporter_id": None,
            "escalation_level": 1,
            "counters": {"unique_reporters": 0, "promotes": 0, "better": 0, "yes": 0, "no": 0, "comments": 0},
            "weather_multiplier": 1.2,
            "created_at": now,
            "updated_at": now,
            "last_progress_at": now,
        }
    )
    score_incident(db, cid, now=now)
    return cid


def _fuse(db: Database, lat: float, lng: float, now: datetime) -> int:
    count = 0
    for incident in db.col("complaints").find({}):
        if canonical(incident.get("status", "")) in {"closed", "closed_unverified"}:
            continue
        if incident.get("source") == "auto_weather":
            continue
        if incident.get("latitude") is None:
            continue
        cat = db.col("categories").find_one({"_id": incident.get("category_id")}) or {}
        if cat.get("slug") not in FUSE_CATEGORIES and incident.get("ai_category_slug") not in FUSE_CATEGORIES:
            continue
        if distance_m(lat, lng, incident["latitude"], incident["longitude"]) > FUSE_RADIUS_M:
            continue
        db.col("complaints").update_one(
            {"_id": incident["_id"]},
            {"$set": {"weather_multiplier": 1.4, "updated_at": now}},
        )
        score_incident(db, incident["_id"], now=now)
        count += 1
    return count
