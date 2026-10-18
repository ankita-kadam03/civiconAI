from __future__ import annotations

INCIDENT_STATUSES = (
    "SUBMITTED",
    "ACKNOWLEDGED",
    "IN_PROGRESS",
    "MORE_INFO_REQUESTED",
    "ESCALATED",
    "RESOLVED",
    "CLOSED",
    "REJECTED",
)

SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
ROLES = ("CITIZEN", "OFFICER", "ADMIN")

ALLOWED: dict[str, list[str]] = {
    "SUBMITTED": ["ACKNOWLEDGED", "REJECTED", "ESCALATED"],
    "ACKNOWLEDGED": ["IN_PROGRESS", "MORE_INFO_REQUESTED", "REJECTED", "ESCALATED"],
    "IN_PROGRESS": ["MORE_INFO_REQUESTED", "RESOLVED", "ESCALATED"],
    "MORE_INFO_REQUESTED": ["IN_PROGRESS", "ACKNOWLEDGED", "REJECTED", "ESCALATED"],
    "ESCALATED": ["ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "REJECTED"],
    "RESOLVED": ["CLOSED", "IN_PROGRESS"],
    "CLOSED": [],
    "REJECTED": [],
}


def can_transition(frm: str, to: str) -> bool:
    if frm == to:
        return False
    return to in ALLOWED.get(frm, [])


def assert_transition(frm: str, to: str) -> None:
    if not can_transition(frm, to):
        raise ValueError(f"Status cannot move from {frm} to {to}")


def is_open_status(status: str) -> bool:
    return status not in {"RESOLVED", "CLOSED", "REJECTED"}


def is_privileged_role(role: str) -> bool:
    return role in {"OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3"}
