from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.status import is_open_status


@dataclass
class EscalationRule:
    id: str
    category_id: str | None
    severity: str | None
    level: int
    review_hours: int
    resolve_hours: int
    reason: str
    is_active: bool = True


@dataclass
class EscalationCandidate:
    id: str
    category_id: str
    status: str
    severity: str
    assigned_officer_id: str | None
    created_at: datetime
    last_progress_at: datetime
    existing_levels: list[int]


@dataclass
class EscalationDecision:
    incident_id: str
    level: int
    reason: str
    idempotency_key: str


def hours_between(frm: datetime, to: datetime, time_scale: float = 1) -> float:
    scale = time_scale if time_scale > 0 else 1
    return ((to - frm).total_seconds() / 3600.0) * scale


def matching_rule(rules: list[EscalationRule], incident: EscalationCandidate) -> EscalationRule | None:
    active = sorted([r for r in rules if r.is_active], key=lambda r: r.level)
    return next(
        (
            r
            for r in active
            if r.category_id == incident.category_id and r.severity == incident.severity
        ),
        next(
            (r for r in active if r.category_id == incident.category_id and not r.severity),
            next(
                (r for r in active if not r.category_id and r.severity == incident.severity),
                next((r for r in active if not r.category_id and not r.severity), None),
            ),
        ),
    )


def evaluate_incident(
    incident: EscalationCandidate,
    rule: EscalationRule | None,
    now: datetime,
    time_scale: float = 1,
) -> EscalationDecision | None:
    if not rule or not is_open_status(incident.status):
        return None

    age_hours = hours_between(incident.created_at, now, time_scale)
    idle_hours = hours_between(incident.last_progress_at, now, time_scale)
    last = incident.existing_levels[-1] if incident.existing_levels else 0
    next_level = last + 1
    if next_level > 3:
        return None

    reasons: list[str] = []
    if not incident.assigned_officer_id and age_hours >= min(rule.review_hours, 12):
        reasons.append("Unassigned beyond the review window")
    if incident.status == "SUBMITTED" and age_hours >= rule.review_hours:
        reasons.append("Unreviewed past the category review target")
    if age_hours >= rule.resolve_hours:
        reasons.append("Resolution target exceeded")
    if incident.severity in {"HIGH", "CRITICAL"} and idle_hours >= max(6, rule.review_hours / 2):
        reasons.append("High-priority incident with no recent progress")

    if not reasons:
        return None

    if incident.existing_levels and idle_hours < max(1.0, rule.review_hours / 2):
        return None

    level = min(next_level, 3)
    if level in incident.existing_levels:
        return None

    return EscalationDecision(
        incident_id=incident.id,
        level=level,
        reason="; ".join(reasons),
        idempotency_key=f"{incident.id}:level:{level}",
    )


def evaluate_batch(
    incidents: list[EscalationCandidate],
    rules: list[EscalationRule],
    now: datetime,
    time_scale: float = 1,
) -> list[EscalationDecision]:
    seen: set[str] = set()
    out: list[EscalationDecision] = []
    for incident in incidents:
        decision = evaluate_incident(incident, matching_rule(rules, incident), now, time_scale)
        if not decision or decision.idempotency_key in seen:
            continue
        seen.add(decision.idempotency_key)
        out.append(decision)
    return out
