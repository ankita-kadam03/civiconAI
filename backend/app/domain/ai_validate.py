from __future__ import annotations

import json
import re

from app.domain.status import SEVERITIES

ALLOWED_SLUGS = {
    "potholes",
    "garbage",
    "water",
    "drainage",
    "streetlights",
    "traffic-signs",
    "parks",
    "infrastructure",
    "other",
}

ALLOWED_DEPTS = {"PWD", "SAN", "WTR", "ELC", "TRF", "PRK", "GEN"}


def extract_json(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def validate_classification(raw: dict, known_slugs: set[str] | None = None) -> dict | None:
    slugs = known_slugs or ALLOWED_SLUGS
    slug = str(raw.get("category_slug") or raw.get("category") or "").strip().lower()
    severity = str(raw.get("severity") or "").strip().upper()
    summary = str(raw.get("summary") or "").strip()
    dept = str(raw.get("department_code") or raw.get("department") or "").strip().upper()
    rationale = str(raw.get("rationale") or "").strip()
    if slug not in slugs:
        slug = "other"
    if severity not in SEVERITIES:
        severity = "MEDIUM"
    if not summary or len(summary) > 600:
        return None
    if dept not in ALLOWED_DEPTS:
        dept = "GEN"
    if len(rationale) > 800:
        rationale = rationale[:800]
    return {
        "category_slug": slug,
        "severity": severity,
        "summary": summary,
        "department_code": dept,
        "rationale": rationale or "Generated recommendation",
    }
