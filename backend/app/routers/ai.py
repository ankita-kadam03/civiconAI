from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.db import Database
from app.deps import current_user, db_dep, optional_user
from app.domain.report_images import read_report_images, report_analysis_digest
from app.schemas import ChatIn, ClassifyIn
from app.security import encode_token
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


@router.post("/classify-attachments")
async def classify_attachments(
    title: str = Form(...),
    description: str = Form(...),
    locality: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    user: dict = Depends(current_user),
):
    body = ClassifyIn(title=title, description=description, locality=locality)
    images = await read_report_images(files)
    result = ai_service.classify(
        body.title,
        body.description,
        body.locality,
        photo_count=len(images),
        images=[(data, mime_type) for data, mime_type, _ in images],
    )
    if result.get("source") == "error":
        from app.errors import AppError

        raise AppError(
            result.get("rationale") or "Gemini classification is required but unavailable.",
            503,
            "AI_UNAVAILABLE",
        )
    result["label"] = "Gemini (Vertex AI)" if result.get("ai_generated") else "Heuristic suggestion"
    result["classification_token"] = encode_token(
        {
            "typ": "report-classification",
            "sub": user["_id"],
            "digest": report_analysis_digest(body.title, body.description, body.locality, images),
            "result": result,
        },
        minutes=20,
    )
    return result


@router.post("/chat")
def chat(body: ChatIn, user: dict | None = Depends(optional_user), db: Database = Depends(db_dep)):
    from app.services.civichat import civichat_response

    return civichat_response(
        body.message,
        db,
        user=user,
        history=body.history,
        latitude=body.latitude,
        longitude=body.longitude,
    )
