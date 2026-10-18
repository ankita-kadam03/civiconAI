from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import Database
from app.deps import current_user, db_dep
from app.schemas import ChatIn, ClassifyIn
from app.services.ai import ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/classify")
def classify(body: ClassifyIn, user: dict = Depends(current_user)):
    result = ai_service.classify(body.title, body.description, body.locality, photo_count=body.photo_count or 0)
    if result.get("source") == "error":
        from app.errors import AppError

        raise AppError(
            result.get("rationale") or "Gemini classification is required but unavailable.",
            503,
            "AI_UNAVAILABLE",
        )
    result["label"] = "Gemini (Vertex AI)" if result.get("ai_generated") else "Heuristic suggestion"
    return result


@router.post("/chat")
def chat(body: ChatIn, user: dict = Depends(current_user), db: Database = Depends(db_dep)):
    from app.services.civichat import civichat_reply

    reply = civichat_reply(body.message, db, latitude=body.latitude, longitude=body.longitude)
    return {
        "reply": reply,
        "ai_generated": False,
        "disclaimer": "CiviChat helps with navigation and nearby public reports only.",
    }
