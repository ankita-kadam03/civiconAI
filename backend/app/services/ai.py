from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from app.config import get_settings
from app.domain.ai_validate import validate_classification

log = logging.getLogger("civicon.ai")

KEYWORD_MAP = [
    (("pothole", "crater", "road damage", "asphalt"), "potholes", "PWD", "HIGH"),
    (("garbage", "trash", "waste", "dump", "litter"), "garbage", "SAN", "MEDIUM"),
    (("leak", "water", "pipeline", "tap", "shortage"), "water", "WTR", "HIGH"),
    (("drain", "sewage", "flood", "stagnant"), "drainage", "PWD", "HIGH"),
    (("streetlight", "lamp", "dark", "lighting"), "streetlights", "ELC", "MEDIUM"),
    (("signboard", "signal", "traffic sign"), "traffic-signs", "TRF", "MEDIUM"),
    (("park", "playground", "garden", "swing"), "parks", "PRK", "LOW"),
    (("footpath", "bridge", "wall", "railing"), "infrastructure", "PWD", "MEDIUM"),
]

SYSTEM_CLASSIFY = """You classify civic infrastructure complaints for a municipality.
Return JSON only with keys: category_slug, severity, summary, department_code, rationale.
category_slug must be one of: potholes, garbage, water, drainage, streetlights, traffic-signs, parks, infrastructure, other.
severity must be one of: LOW, MEDIUM, HIGH, CRITICAL.
department_code must be one of: PWD, SAN, WTR, ELC, TRF, PRK, GEN.
summary: one or two sentences for an officer. Do not include personal names, emails, phones, or exact private addresses.
Never invent official policy or claim that authorities have been contacted.
"""

SYSTEM_CHAT = """You are Civicon Helper, a friendly civic reporting assistant.
Help people describe neighbourhood issues and navigate Civicon AI.
Never claim a government agency was contacted. Never invent laws or case status.
Do not ask for passwords, OTP codes, or ID document numbers.
Keep answers short and practical. Label uncertainty clearly.
"""


class AIService:
    def __init__(self) -> None:
        self.mode = "fallback"
        self.error: str | None = None
        self.model_in_use: str | None = None
        self._client: Any = None
        self._client_key: str | None = None
        self.reload_from_settings()

    def reload_from_settings(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        api_key = (settings.gemini_api_key or "").strip()
        project = (settings.google_cloud_project or "").strip()
        fingerprint = f"key:{api_key[:8]}..." if api_key else f"vertex:{project}"
        if self._client is not None and self._client_key == fingerprint:
            return
        self._client = None
        self._client_key = None
        self.mode = "fallback"
        self.error = None
        try:
            from google import genai

            if api_key:
                self._client = genai.Client(api_key=api_key)
                self.mode = "gemini_api"
                self._client_key = fingerprint
            elif project:
                self._client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=settings.google_cloud_location or "us-central1",
                )
                self.mode = "vertex"
                self._client_key = fingerprint
        except Exception as exc:  # noqa: BLE001
            self.mode = "fallback"
            self.error = type(exc).__name__
            log.warning("ai_client_unavailable error=%s", type(exc).__name__)

    def _activate_vertex_fallback(self) -> bool:
        settings = get_settings()
        project = (settings.google_cloud_project or "").strip()
        if not project or self.mode == "vertex":
            return False
        try:
            from google import genai

            self._client = genai.Client(
                vertexai=True,
                project=project,
                location=settings.google_cloud_location or "us-central1",
            )
            self.mode = "vertex"
            self._client_key = f"vertex:{project}"
            self.error = None
            log.info("ai_fallback_to_vertex project=%s", project)
            return True
        except Exception as exc:  # noqa: BLE001
            self.error = type(exc).__name__
            log.warning("ai_vertex_fallback_failed error=%s", type(exc).__name__)
            return False

    def _generate_once(self, system: str, user: str, settings) -> str | None:
        last_error = None
        blocked_key = False
        for model in settings.gemini_model_candidates:
            try:

                def _call(current_model: str = model) -> str | None:
                    response = self._client.models.generate_content(
                        model=current_model,
                        contents=user,
                        config={
                            "system_instruction": system,
                            "temperature": 0.2,
                            "max_output_tokens": 512,
                        },
                    )
                    return getattr(response, "text", None)

                with ThreadPoolExecutor(max_workers=1) as pool:
                    text = pool.submit(_call).result(timeout=18)
                if text:
                    self.model_in_use = model
                    return text
            except FuturesTimeout:
                last_error = "TimeoutError"
                log.warning("ai_generate_timeout model=%s", model)
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = type(exc).__name__
                msg = str(exc)
                if any(
                    token in msg
                    for token in (
                        "API_KEY_SERVICE_BLOCKED",
                        "PERMISSION_DENIED",
                        "RESOURCE_EXHAUSTED",
                        "no longer available",
                        "NOT_FOUND",
                    )
                ):
                    blocked_key = True
                log.warning("ai_generate_failed model=%s error=%s", model, type(exc).__name__)
                continue
        self.error = last_error
        if blocked_key and self._activate_vertex_fallback():
            return self._generate_once(system, user, settings)
        return None

    def _generate(self, system: str, user: str) -> str | None:
        self.reload_from_settings()
        if not self._client:
            if self._activate_vertex_fallback():
                pass
            if not self._client:
                return None
        settings = get_settings()
        return self._generate_once(system, user, settings)

    def classify(
        self,
        title: str,
        description: str,
        locality: str | None = None,
        *,
        photo_count: int = 0,
    ) -> dict:
        self.reload_from_settings()
        settings = get_settings()
        if settings.require_gemini and not self._client:
            return {
                "category_slug": "other",
                "severity": "MEDIUM",
                "summary": title.strip()[:180],
                "department_code": "GEN",
                "rationale": "Set GEMINI_API_KEY in backend/.env and restart the API (or use Vertex via GOOGLE_CLOUD_PROJECT + ADC).",
                "source": "error",
                "ai_generated": False,
                "error": "Gemini not configured",
            }
        heuristic = heuristic_classify(title, description)
        photo_note = ""
        if photo_count > 0:
            photo_note = f"\nPhotos attached: {photo_count}. Consider visual evidence in severity (officers will review images).\n"
        prompt = (
            f"Title: {title[:140]}\n"
            f"Description: {description[:800]}\n"
            f"Locality: {(locality or 'unspecified')[:80]}\n"
            f"{photo_note}"
        )
        text = self._generate(SYSTEM_CLASSIFY, prompt)
        if not text:
            if settings.require_gemini:
                heuristic["source"] = "error"
                heuristic["ai_generated"] = False
                heuristic["error"] = "Gemini classification unavailable"
                detail = self.error or "model request failed"
                heuristic["rationale"] = (
                    f"Gemini call failed ({detail}). "
                    "For API keys: enable Generative Language API and add AI Studio credits, or leave GEMINI_API_KEY empty to use Vertex AI (GCP billing)."
                )
                return heuristic
            heuristic["source"] = "heuristic"
            heuristic["ai_generated"] = False
            return heuristic
        from app.domain.ai_validate import extract_json

        parsed = _parse_classification(text)
        if not parsed:
            retry_prompt = (
                f"{prompt}\n\nReturn ONLY a single JSON object with keys "
                "category_slug, severity, summary, department_code, rationale. No markdown."
            )
            text = self._generate(SYSTEM_CLASSIFY, retry_prompt)
            parsed = _parse_classification(text) if text else None
        if not parsed:
            if settings.require_gemini:
                heuristic["source"] = "error"
                heuristic["ai_generated"] = False
                heuristic["error"] = "Invalid model response"
                heuristic["rationale"] = "Gemini responded but JSON was invalid; try again."
                return heuristic
            heuristic["source"] = "heuristic"
            heuristic["ai_generated"] = False
            return heuristic
        parsed["source"] = self.mode
        parsed["ai_generated"] = True
        return parsed

    def chat(self, message: str, history: list[dict[str, str]] | None = None) -> str:
        hist = ""
        for item in (history or [])[-6]:
            role = item.get("role", "user")
            if role not in {"user", "assistant"}:
                continue
            hist += f"{role}: {item.get('content', '')[:400]}\n"
        user = f"{hist}user: {message[:1200]}"
        text = self._generate(SYSTEM_CHAT, user)
        if text:
            return text.strip()
        return fallback_chat(message)

    def health(self) -> dict:
        return {
            "status": "configured" if self._client else "fallback",
            "mode": self.mode,
            "model": self.model_in_use or get_settings().gemini_model_candidates[0],
            "error": self.error,
        }


def _parse_classification(text: str) -> dict | None:
    from app.domain.ai_validate import extract_json, validate_classification

    raw = extract_json(text) or {}
    return validate_classification(raw)


def heuristic_classify(title: str, description: str) -> dict:
    blob = f"{title} {description}".lower()
    for words, slug, dept, severity in KEYWORD_MAP:
        if any(word in blob for word in words):
            return {
                "category_slug": slug,
                "severity": severity,
                "summary": title.strip()[:180],
                "department_code": dept,
                "rationale": "Keyword fallback because a live model response was unavailable or invalid.",
                "source": "heuristic",
                "ai_generated": False,
            }
    return {
        "category_slug": "other",
        "severity": "MEDIUM",
        "summary": title.strip()[:180],
        "department_code": "GEN",
        "rationale": "No confident category match. Routed to general administration.",
        "source": "heuristic",
        "ai_generated": False,
    }


def fallback_chat(message: str) -> str:
    text = message.lower()
    if any(w in text for w in ("report", "pothole", "garbage", "light", "water")):
        return (
            "You can file a report from Report an issue. Add a short title, what you saw, "
            "the locality, and an optional photo. After you submit, you will receive a CIV reference number to track progress."
        )
    if "track" in text or "status" in text:
        return "Open My reports and search by your CIV reference. Status updates appear on the incident timeline."
    if "officer" in text or "admin" in text:
        return "Officers use Assigned incidents. Administrators manage users, categories, and escalation rules from the admin dashboard."
    return (
        "I can help you prepare a civic report or find a page in Civicon AI. "
        "Tell me what you noticed in your neighbourhood — for example a pothole, a dark streetlight, or overflowing bins."
    )


def similar_score(a: dict, b: dict) -> float:
    text_a = f"{a.get('title','')} {a.get('description','')}".lower()
    text_b = f"{b.get('title','')} {b.get('description','')}".lower()
    words_a = set(re.findall(r"[a-z]{3,}", text_a))
    words_b = set(re.findall(r"[a-z]{3,}", text_b))
    if not words_a or not words_b:
        overlap = 0.0
    else:
        overlap = len(words_a & words_b) / len(words_a | words_b)
    score = overlap
    if a.get("category_id") and a.get("category_id") == b.get("category_id"):
        score += 0.25
    if a.get("latitude") is not None and b.get("latitude") is not None:
        dist = haversine(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
        if dist < 0.3:
            score += 0.3
        elif dist < 1:
            score += 0.15
    return score


def haversine(lat1, lon1, lat2, lon2) -> float:
    from math import atan2, cos, radians, sin, sqrt

    if None in (lat1, lon1, lat2, lon2):
        return 999
    r = 6371
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * atan2(sqrt(h), sqrt(1 - h))


ai_service = AIService()
