from __future__ import annotations

import hashlib
import json

from fastapi import UploadFile

from app.domain.files import MAX_FILE_BYTES, validate_upload
from app.errors import AppError

MAX_REPORT_ATTACHMENTS = 4


async def read_report_images(files: list[UploadFile]) -> list[tuple[bytes, str, str]]:
    if len(files) > MAX_REPORT_ATTACHMENTS:
        raise AppError(f"A report can include up to {MAX_REPORT_ATTACHMENTS} images.", 400, "TOO_MANY_FILES")
    images: list[tuple[bytes, str, str]] = []
    for file in files:
        data = await file.read(MAX_FILE_BYTES + 1)
        mime_type = file.content_type or ""
        original_name = file.filename or "upload"
        ok, error = validate_upload(mime_type, len(data), original_name)
        if not ok:
            raise AppError(error, 400, "INVALID_FILE")
        images.append((data, mime_type, original_name))
    return images


def report_analysis_digest(
    title: str,
    description: str,
    locality: str | None,
    images: list[tuple[bytes, str, str]],
) -> str:
    digest = hashlib.sha256()
    fields = json.dumps(
        [title.strip(), description.strip(), (locality or "").strip()],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest.update(fields.encode("utf-8"))
    for data, mime_type, _ in images:
        digest.update(mime_type.encode("utf-8"))
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()
