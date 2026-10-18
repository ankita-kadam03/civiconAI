from __future__ import annotations

SPEC_STATUSES = (
    "reported",
    "triaged",
    "assigned",
    "in_progress",
    "resolved_pending_verification",
    "closed",
    "closed_unverified",
    "reopened",
)

LEGACY_TO_SPEC = {
    "SUBMITTED": "reported",
    "ACKNOWLEDGED": "triaged",
    "IN_PROGRESS": "in_progress",
    "MORE_INFO_REQUESTED": "in_progress",
    "ESCALATED": "in_progress",
    "RESOLVED": "resolved_pending_verification",
    "CLOSED": "closed",
    "REJECTED": "closed",
}

SPEC_TO_LEGACY = {
    "reported": "SUBMITTED",
    "triaged": "ACKNOWLEDGED",
    "assigned": "ACKNOWLEDGED",
    "in_progress": "IN_PROGRESS",
    "resolved_pending_verification": "RESOLVED",
    "closed": "CLOSED",
    "closed_unverified": "CLOSED",
    "reopened": "IN_PROGRESS",
}

LIFE_SAFETY_CATEGORIES = {
    "fire",
    "electrical",
    "electrical-hazard",
    "collapse",
    "flooding",
    "injury",
    "gas",
    "crime",
}

CATEGORY_GROUP = {
    "drainage": "water",
    "water": "water",
    "flooding": "water",
    "garbage": "waste",
    "potholes": "roads",
    "infrastructure": "roads",
    "collapse": "roads",
    "streetlights": "lighting",
    "electrical": "power",
    "fire": "safety",
    "injury": "safety",
    "gas": "safety",
    "crime": "safety",
}

GROUP_RADIUS_M = {
    "water": 500,
    "waste": 200,
    "roads": 300,
    "lighting": 150,
    "power": 300,
    "safety": 400,
}

OPEN_SPEC = {
    "reported",
    "triaged",
    "assigned",
    "in_progress",
    "reopened",
    "resolved_pending_verification",
}

ACKED = {"assigned", "in_progress", "resolved_pending_verification", "closed", "closed_unverified", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "CLOSED"}
RESOLVED = {"resolved_pending_verification", "closed", "closed_unverified", "RESOLVED", "CLOSED"}


def canonical(status: str) -> str:
    return LEGACY_TO_SPEC.get(status, status)


def legacy(status: str) -> str:
    if status in LEGACY_TO_SPEC:
        return status
    return SPEC_TO_LEGACY.get(status, status.upper())


def is_open_lifecycle(status: str) -> bool:
    return canonical(status) not in {"closed", "closed_unverified"}
