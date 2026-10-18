from __future__ import annotations

import uuid
from datetime import datetime, timezone

ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

MAX_FILE_BYTES = 8 * 1024 * 1024

EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
}


def validate_upload(mimetype: str, size: int, original_name: str) -> tuple[bool, str]:
    if not mimetype:
        return False, "No file provided"
    if mimetype not in ALLOWED_MIME:
        return False, "Only JPEG, PNG, WebP, or HEIC images are allowed"
    if size <= 0 or size > MAX_FILE_BYTES:
        return False, "Each photo must be 8 MB or smaller"
    name = (original_name or "").lower()
    if ".." in name or "/" in name or "\\" in name:
        return False, "Invalid file name"
    return True, EXT.get(mimetype, "bin")


def random_object_key(prefix: str, ext: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{prefix}/{day}/{uuid.uuid4().hex}.{ext}"
