from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

log = logging.getLogger("civicon.bigquery")

TABLE_ID = "incidents"


class BigQueryAnalytics:
    def __init__(self) -> None:
        self._client: Any = None
        self.error: str | None = None
        self.dataset_id: str | None = None
        self.table_fqn: str | None = None

    def _settings_ok(self) -> bool:
        settings = get_settings()
        return bool(settings.bigquery_dataset.strip() and settings.google_cloud_project.strip())

    def connect(self) -> None:
        settings = get_settings()
        self.dataset_id = settings.bigquery_dataset.strip()
        project = settings.google_cloud_project.strip()
        if not self.dataset_id or not project:
            self.error = "BIGQUERY_DATASET and GOOGLE_CLOUD_PROJECT are required"
            return
        try:
            from google.cloud import bigquery

            self._client = bigquery.Client(project=project)
            self.table_fqn = f"{project}.{self.dataset_id}.{TABLE_ID}"
            self._ensure_schema()
            self.error = None
        except Exception as exc:  # noqa: BLE001
            self._client = None
            self.error = type(exc).__name__
            log.warning("bigquery_connect_failed error=%s", self.error)

    def _ensure_schema(self) -> None:
        from google.cloud import bigquery

        assert self._client is not None
        assert self.dataset_id is not None
        project = get_settings().google_cloud_project.strip()
        dataset_ref = f"{project}.{self.dataset_id}"
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = get_settings().google_cloud_location or "us-central1"
        try:
            self._client.create_dataset(dataset, exists_ok=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("bigquery_dataset_ensure error=%s", type(exc).__name__)

        schema = [
            bigquery.SchemaField("incident_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("reference", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("status", "STRING"),
            bigquery.SchemaField("severity", "STRING"),
            bigquery.SchemaField("category_name", "STRING"),
            bigquery.SchemaField("department_name", "STRING"),
            bigquery.SchemaField("locality", "STRING"),
            bigquery.SchemaField("latitude", "FLOAT"),
            bigquery.SchemaField("longitude", "FLOAT"),
            bigquery.SchemaField("reporter_id", "STRING"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("updated_at", "TIMESTAMP"),
            bigquery.SchemaField("resolved_at", "TIMESTAMP"),
        ]
        table = bigquery.Table(self.table_fqn, schema=schema)
        self._client.create_table(table, exists_ok=True)

    def health(self) -> dict:
        settings = get_settings()
        if not settings.bigquery_dataset.strip():
            return {"configured": False, "status": "missing_dataset", "error": "BIGQUERY_DATASET not set"}
        if not self._client:
            return {
                "configured": True,
                "status": "error",
                "dataset": settings.bigquery_dataset,
                "error": self.error,
            }
        try:
            self._client.get_table(self.table_fqn)
            status = "connected"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            self.error = type(exc).__name__
        return {
            "configured": True,
            "status": status,
            "dataset": settings.bigquery_dataset,
            "table": TABLE_ID,
            "error": self.error,
        }

    def sync_incident(
        self,
        doc: dict,
        *,
        category_name: str | None = None,
        department_name: str | None = None,
    ) -> None:
        if not self._client or not self.table_fqn:
            return

        def ts(value: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            return str(value)

        row = {
            "incident_id": doc.get("_id"),
            "reference": doc.get("reference"),
            "title": (doc.get("title") or "")[:500],
            "status": doc.get("status"),
            "severity": doc.get("severity"),
            "category_name": category_name,
            "department_name": department_name,
            "locality": doc.get("locality"),
            "latitude": doc.get("latitude"),
            "longitude": doc.get("longitude"),
            "reporter_id": doc.get("reporter_id"),
            "created_at": ts(doc.get("created_at")),
            "updated_at": ts(doc.get("updated_at")),
            "resolved_at": ts(doc.get("resolved_at")),
        }
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("id", "STRING", row["incident_id"]),
            ]
        )
        delete_sql = f"DELETE FROM `{self.table_fqn}` WHERE incident_id = @id"
        self._client.query(delete_sql, job_config=job_config).result()
        errors = self._client.insert_rows_json(self.table_fqn, [row])
        if errors:
            log.warning("bigquery_insert_errors count=%s", len(errors))

    def backfill_from_db(self, db) -> int:
        if not self._client:
            return 0
        n = 0
        for doc in db.col("complaints").find({}):
            cat = db.col("categories").find_one({"_id": doc.get("category_id")}) or {}
            dept = db.col("departments").find_one({"_id": doc.get("department_id")}) or {}
            self.sync_incident(
                doc,
                category_name=cat.get("name"),
                department_name=dept.get("name"),
            )
            n += 1
        return n

    def recurrence_hotspots(self, *, days: int = 60, limit: int = 10) -> list[dict]:
        if not self._client or not self.table_fqn:
            return []
        sql = f"""
        SELECT
          COALESCE(locality, 'Unknown') AS locality,
          COALESCE(category_name, 'Unknown') AS category,
          COUNT(*) AS incident_count
        FROM `{self.table_fqn}`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        GROUP BY locality, category
        HAVING COUNT(*) >= 2
        ORDER BY incident_count DESC
        LIMIT @lim
        """
        from google.cloud import bigquery

        job = self._client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("days", "INT64", days),
                    bigquery.ScalarQueryParameter("lim", "INT64", limit),
                ]
            ),
        )
        return [
            {"locality": row.locality, "category": row.category, "count": int(row.incident_count)}
            for row in job.result()
        ]

    def ai_summary_context(self) -> dict:
        """Aggregate stats for optional Gemini narrative on admin dashboard."""
        if not self._client or not self.table_fqn:
            return {}
        sql = f"""
        SELECT
          COUNT(*) AS total,
          COUNTIF(status IN ('SUBMITTED','ACKNOWLEDGED','IN_PROGRESS','ESCALATED','MORE_INFO_REQUESTED')) AS open_count,
          COUNTIF(created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)) AS last_7_days
        FROM `{self.table_fqn}`
        """
        row = next(self._client.query(sql).result(), None)
        if not row:
            return {}
        return {"total": row.total, "open": row.open_count, "last_7_days": row.last_7_days}


bigquery_analytics = BigQueryAnalytics()
