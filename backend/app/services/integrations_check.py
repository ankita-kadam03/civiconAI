from __future__ import annotations

import logging

from app.config import get_settings
from app.services.ai import ai_service
from app.services.bigquery_analytics import bigquery_analytics

log = logging.getLogger("civicon")


def assert_required_integrations(*, strict: bool | None = None) -> list[str]:
    """Validate Gemini/Vertex and BigQuery are configured. Returns warnings; raises if strict."""
    settings = get_settings()
    use_strict = settings.require_gemini if strict is None else strict
    problems: list[str] = []

    if settings.require_gemini:
        has_key = bool((settings.gemini_api_key or "").strip())
        has_vertex = bool((settings.google_cloud_project or "").strip())
        if not has_key and not has_vertex:
            problems.append("REQUIRE_GEMINI: set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT for Vertex AI")
        elif ai_service.health().get("status") == "fallback":
            problems.append("Gemini client failed to initialize (check API key and enabled APIs)")

    if settings.require_bigquery:
        if not (settings.bigquery_dataset or "").strip():
            problems.append("REQUIRE_BIGQUERY: set BIGQUERY_DATASET (e.g. civicon_analytics)")
        elif not (settings.google_cloud_project or "").strip():
            problems.append("REQUIRE_BIGQUERY: set GOOGLE_CLOUD_PROJECT")
        else:
            bigquery_analytics.connect()
            health = bigquery_analytics.health()
            if health.get("status") == "error":
                problems.append(f"BigQuery not reachable: {health.get('error')}")

    for msg in problems:
        log.error("integration_required %s", msg)

    if use_strict and problems:
        raise RuntimeError("Required integrations missing: " + "; ".join(problems))

    return problems
