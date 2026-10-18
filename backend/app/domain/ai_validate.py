from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.status import SEVERITIES

CategorySlugLLM = Literal[
    "potholes",
    "garbage",
    "water",
    "drainage",
    "streetlights",
    "traffic-signs",
    "parks",
    "infrastructure",
    "other",
]
SeverityLLM = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
DepartmentLLM = Literal["PWD", "SAN", "WTR", "ELC", "TRF", "PRK", "GEN"]


class ClassificationLLMOut(BaseModel):
    """JSON schema for Gemini / Vertex structured classification output."""

    category_slug: CategorySlugLLM = Field(
        description="Infrastructure category slug for routing the complaint.",
    )
    severity: SeverityLLM = Field(description="Urgency for municipal response.")
    summary: str = Field(
        min_length=1,
        max_length=600,
        description="One or two sentences for an officer; no PII or exact private addresses.",
    )
    department_code: DepartmentLLM = Field(description="Department code to assign.")
    rationale: str = Field(
        default="Generated recommendation",
        max_length=800,
        description="Brief reason for category and severity.",
    )

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


def validate_classification(
    raw: dict,
    known_slugs: set[str] | None = None,
    *,
    fallback_title: str = "",
) -> dict | None:
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
    if not summary:
        summary = fallback_title.strip()[:180]
    if not summary:
        return None
    if len(summary) > 600:
        summary = summary[:600]
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


def classification_from_llm(
    llm: ClassificationLLMOut,
    *,
    fallback_title: str = "",
) -> dict | None:
    return validate_classification(llm.model_dump(), fallback_title=fallback_title)
