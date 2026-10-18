from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings

log = logging.getLogger("civicon.pubsub")


class PubSubService:
    def __init__(self) -> None:
        self.mode = "disabled"
        self.error: str | None = None
        self._publisher: Any = None
        self._path: str | None = None
        settings = get_settings()
        if not settings.google_cloud_project or not settings.pubsub_topic_events:
            return
        try:
            from google.cloud import pubsub_v1

            self._publisher = pubsub_v1.PublisherClient()
            self._path = self._publisher.topic_path(settings.google_cloud_project, settings.pubsub_topic_events)
            self.mode = "pubsub"
        except Exception as exc:  # noqa: BLE001
            self.error = type(exc).__name__
            log.warning("pubsub_unavailable error=%s", type(exc).__name__)

    def publish(self, event_type: str, payload: dict) -> bool:
        if self.mode != "pubsub" or not self._publisher or not self._path:
            return False
        try:
            body = json.dumps({"type": event_type, **payload}, default=str).encode("utf-8")
            future = self._publisher.publish(self._path, body, event_type=event_type)
            future.result(timeout=8)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("pubsub_publish_failed type=%s error=%s", event_type, type(exc).__name__)
            return False

    def health(self) -> dict:
        return {
            "status": "ok" if self.mode == "pubsub" else "unconfigured",
            "mode": self.mode,
            "configured": bool(get_settings().pubsub_topic_events),
            "error": self.error,
        }


pubsub_service = PubSubService()
