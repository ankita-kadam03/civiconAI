from __future__ import annotations

import math
from datetime import datetime, timedelta

from app.config import get_settings
from app.domain.lifecycle import LIFE_SAFETY_CATEGORIES

SLA_MINUTES = {
    "Critical": {"ack": 15, "resolve": 4 * 60, "l3": 60},
    "High": {"ack": 60, "resolve": 24 * 60, "l3": 12 * 60},
    "Medium": {"ack": 4 * 60, "resolve": 72 * 60, "l3": 48 * 60},
    "Low": {"ack": 24 * 60, "resolve": 7 * 24 * 60, "l3": None},
}


def priority_score(
    *,
    ai: float,
    corroboration: float,
    community: float,
    exposure: float,
    urgency: float,
    reporters: int,
) -> tuple[int, list[dict]]:
    parts = [
        ("AI severity", 0.30, ai, "Model severity, or the category base when review is required"),
        ("Corroboration", 0.25, corroboration, f"{reporters} unique reporters in 24h"),
        ("Community", 0.15, community, "Promotes, reduced when people say it is currently better"),
        ("Exposure", 0.15, exposure, "Nearby school, hospital, main road, or low-lying area" if exposure else "No sensitive site within 300m"),
        ("Urgency", 0.15, urgency, "Age against the acknowledge window"),
    ]
    total = 0.0
    factors: list[dict] = []
    for name, weight, value, detail in parts:
        bounded = min(1.0, max(0.0, value))
        total += weight * bounded
        factors.append({"name": name, "value": round(bounded, 4), "detail": detail})
    return max(0, min(100, int(round(100 * total)))), factors


def label_for(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def community_factor(promotes: int, better: int) -> float:
    raw = min(1.0, math.log1p(max(promotes, 0)) / math.log(21))
    return raw / (1 + max(better, 0))


def urgency_factor(age: timedelta, ack: timedelta, weather: float) -> float:
    if ack.total_seconds() <= 0:
        base = 1.0
    else:
        base = min(1.0, max(0.0, age.total_seconds()) / ack.total_seconds())
    return min(1.0, base * max(weather, 0))


def scaled_minutes(minutes: int) -> timedelta:
    scale = get_settings().demo_time_scale if get_settings().demo_time_scale > 0 else 1
    return timedelta(minutes=minutes / scale)


def deadlines_for(label: str, anchor: datetime) -> dict:
    table = SLA_MINUTES[label]
    return {
        "ack_due": anchor + scaled_minutes(table["ack"]),
        "resolve_due": anchor + scaled_minutes(table["resolve"]),
    }


def life_safety(category: str, ai: dict | None) -> bool:
    if category in LIFE_SAFETY_CATEGORIES:
        return True
    risk = (ai or {}).get("life_safety_risk") or {}
    return bool(risk.get("flag") and float(risk.get("confidence") or 0) >= 0.6)


def category_base_severity(slug: str) -> float:
    table = {
        "fire": 0.95,
        "electrical": 0.85,
        "flooding": 0.8,
        "drainage": 0.55,
        "water": 0.55,
        "potholes": 0.45,
        "garbage": 0.35,
        "streetlights": 0.3,
        "parks": 0.25,
        "other": 0.3,
    }
    return table.get(slug, 0.4)
