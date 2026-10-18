from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config import BACKEND_DIR, get_settings
from app.domain.files import random_object_key, validate_upload

log = logging.getLogger("civicon.storage")
UPLOAD_ROOT = BACKEND_DIR / "uploads"


class StorageService:
    def __init__(self) -> None:
        self.mode = "local"
        self.bucket_name: str | None = None
        self.error: str | None = None
        self._client: Any = None
        self._bucket: Any = None
        settings = get_settings()
        if settings.gcs_bucket:
            try:
                from google.cloud import storage as gcs

                self._client = gcs.Client(project=settings.google_cloud_project or None)
                self._bucket = self._client.bucket(settings.gcs_bucket)
                self._bucket.reload()
                self.mode = "gcs"
                self.bucket_name = settings.gcs_bucket
            except Exception as exc:  # noqa: BLE001
                self.mode = "local"
                self.error = type(exc).__name__
                log.warning("gcs_unavailable fallback=local error=%s", type(exc).__name__)
        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, content_type: str, original_name: str, prefix: str) -> str:
        ok, ext_or_err = validate_upload(content_type, len(data), original_name)
        if not ok:
            raise ValueError(ext_or_err)
        key = random_object_key(prefix, ext_or_err)
        if self.mode == "gcs" and self._bucket is not None:
            blob = self._bucket.blob(key)
            blob.upload_from_string(data, content_type=content_type)
            return key
        path = UPLOAD_ROOT / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def delete(self, key: str) -> None:
        if not key or ".." in key:
            return
        try:
            if self.mode == "gcs" and self._bucket is not None:
                blob = self._bucket.blob(key)
                if blob.exists():
                    blob.delete()
                return
            path = (UPLOAD_ROOT / key).resolve()
            if str(path).startswith(str(UPLOAD_ROOT.resolve())) and path.is_file():
                path.unlink()
        except Exception as exc:  # noqa: BLE001
            log.warning("storage_delete_failed key=%s error=%s", key, type(exc).__name__)

    def load(self, key: str) -> bytes:
        if ".." in key:
            raise ValueError("Invalid object key")
        if self.mode == "gcs" and self._bucket is not None:
            return self._bucket.blob(key).download_as_bytes()
        path = (UPLOAD_ROOT / key).resolve()
        if not str(path).startswith(str(UPLOAD_ROOT.resolve())):
            raise ValueError("Invalid object key")
        return path.read_bytes()

    def health(self) -> dict:
        return {
            "status": "ok" if not self.error else "degraded",
            "mode": self.mode,
            "configured": bool(get_settings().gcs_bucket),
            "error": self.error,
        }


storage_service = StorageService()
