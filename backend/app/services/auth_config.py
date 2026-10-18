from __future__ import annotations

from app.config import Settings

_PLACEHOLDER_MARKERS = (
    "replace-before-production",
    "changeme",
    "change-me",
    "your-secret",
    "your_jwt",
    "todo",
    "example",
    "local-dev-jwt-signing-key",
)


def jwt_auth_health(settings: Settings) -> dict:
    """Public integration status for JWT signing — never includes the secret."""
    secret = (settings.jwt_secret or "").strip()
    if not secret:
        if settings.is_production:
            return {
                "status": "missing",
                "configured": False,
                "provider": "jwt",
                "hint": "Mount JWT_SECRET from Google Secret Manager on Cloud Run (random 32+ chars).",
            }
        return {
            "status": "dev_fallback",
            "configured": True,
            "provider": "jwt",
            "hint": "Local dev uses a built-in signing key. Set JWT_SECRET before production deploy.",
        }

    lower = secret.lower()
    if any(marker in lower for marker in _PLACEHOLDER_MARKERS):
        return {
            "status": "placeholder",
            "configured": False,
            "provider": "jwt",
            "hint": "JWT_SECRET still looks like a template. Generate a random secret and store it in Secret Manager.",
        }
    if len(secret) < 32:
        return {
            "status": "weak",
            "configured": True,
            "provider": "jwt",
            "hint": "Use at least 32 random characters for JWT_SECRET.",
        }
    return {"status": "ok", "configured": True, "provider": "jwt", "hint": None}
