from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("civicon.firestore")

try:
    from google.cloud import firestore
except ImportError:  # pragma: no cover
    firestore = None  # type: ignore


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


def _deserialize(value: Any) -> Any:
    if hasattr(value, "timestamp"):  # Firestore timestamp
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if isinstance(value, dict):
        return {k: _deserialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deserialize(v) for v in value]
    return value


class FirestoreBackend:
    """Persist MemoryCollection mutations to Cloud Firestore."""

    def __init__(self, project_id: str) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is not installed")
        self.client = firestore.Client(project=project_id)

    def collection(self, name: str):
        return self.client.collection(name)

    def hydrate_collection(self, memory_col: Any, name: str) -> int:
        count = 0
        for snap in self.collection(name).stream():
            data = snap.to_dict() or {}
            doc_id = data.get("_id") or snap.id
            data["_id"] = doc_id
            memory_col._docs.append(_deserialize(data))
            count += 1
        return count

    def write_doc(self, collection: str, doc: dict) -> None:
        doc_id = str(doc.get("_id") or "")
        if not doc_id:
            return
        payload = _serialize({k: v for k, v in doc.items() if k != "_id"})
        self.collection(collection).document(doc_id).set(payload, merge=True)

    def delete_doc(self, collection: str, doc_id: str) -> None:
        self.collection(collection).document(str(doc_id)).delete()

    def wipe_collection(self, name: str) -> None:
        batch_size = 200
        col = self.collection(name)
        while True:
            docs = list(col.limit(batch_size).stream())
            if not docs:
                break
            batch = self.client.batch()
            for snap in docs:
                batch.delete(snap.reference)
            batch.commit()

    def wipe_all(self, names: tuple[str, ...]) -> None:
        for name in names:
            try:
                self.wipe_collection(name)
            except Exception as exc:  # noqa: BLE001
                log.warning("firestore_wipe_failed collection=%s error=%s", name, type(exc).__name__)
