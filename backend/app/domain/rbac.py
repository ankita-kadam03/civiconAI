from __future__ import annotations

from dataclasses import dataclass

from app.domain.status import is_privileged_role


@dataclass(frozen=True)
class Principal:
    id: str
    role: str
    department_id: str | None = None


STAFF_ROLES = {"OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3"}
OVERSIGHT_ROLES = {"ADMIN", "ADMIN_L2", "ADMIN_L3"}


def can_read_incident(
    principal: Principal,
    incident: dict,
    *,
    public_view: bool = False,
) -> bool:
    if public_view and incident.get("is_public"):
        return True
    if principal.role in OVERSIGHT_ROLES:
        return True
    if principal.id == incident.get("reporter_id"):
        return True
    if incident.get("is_public") and principal.role == "CITIZEN":
        return True
    if principal.role in {"OFFICER", "ADMIN_L1"}:
        if incident.get("assigned_officer_id") == principal.id:
            return True
        if incident.get("claimed_by") == principal.id:
            return True
        if principal.department_id and incident.get("department_id") == principal.department_id:
            return True
        if not incident.get("assigned_officer_id"):
            return True
    return False


def can_update_incident(principal: Principal, incident: dict) -> bool:
    if principal.role in OVERSIGHT_ROLES:
        return True
    if principal.role in {"OFFICER", "ADMIN_L1"}:
        if incident.get("assigned_officer_id") == principal.id:
            return True
        if incident.get("claimed_by") == principal.id:
            return True
        if principal.department_id and incident.get("department_id") == principal.department_id:
            return True
        if not incident.get("assigned_officer_id"):
            return True
    if principal.id == incident.get("reporter_id") and incident.get("status") == "MORE_INFO_REQUESTED":
        return True
    return False


def can_view_internal_notes(principal: Principal) -> bool:
    return is_privileged_role(principal.role)


def can_manage_users(principal: Principal) -> bool:
    return principal.role in {"ADMIN", "ADMIN_L3"}


def can_self_assign_role() -> bool:
    return False
