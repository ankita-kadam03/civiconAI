# Google Cloud setup for Civicon AI

Do not create resources, enable extra APIs, change IAM, or deploy until the project owner approves. These steps may incur charges.

## Authentication

Local development should use Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Prefer an attached Cloud Run service account in production. Do not commit service-account JSON keys.

## Vertex AI / Gemini (required)

Set `REQUIRE_GEMINI=true` (default). You must configure **either**:

1. `GEMINI_API_KEY` (Gemini Developer API), **or**
2. `GOOGLE_CLOUD_PROJECT` + Application Default Credentials for Vertex AI.

Enable `generativelanguage.googleapis.com` and/or `aiplatform.googleapis.com`. Report submission and `/api/ai/classify` return **503** if Gemini is unavailable when required.

Humans can override every AI suggestion in the UI.

## Cloud Storage

Set `GCS_BUCKET` to a private bucket. Objects use random names. The API streams files after server-side authorization. Do not make the bucket public to display images.

IAM needed by the runtime identity: `storage.objects.create`, `storage.objects.get` on that bucket.

## Pub/Sub

Topic name is `PUBSUB_TOPIC_EVENTS` (default `incident-events`). Events: `incident.created`, `incident.status_changed`, `incident.escalated`.

Push endpoint: `POST /internal/events` authenticated with `INTERNAL_TASK_SECRET` (or OIDC later via `PUSH_SERVICE_ACCOUNT` / `INTERNAL_OIDC_AUDIENCE`). Consumers are idempotent via `processed_events`.

If the topic does not exist, the app still runs and skips publish failures.

## Cloud Scheduler / Cloud Run Jobs

Schedule `POST /internal/tasks/escalate` on a short interval. The job is idempotent: the same level is never written twice.

Local equivalent: `python -m app.jobs.escalate` from `backend/`.

## Cloud Run

`backend/Dockerfile` serves `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`.

Suggested runtime env: `APP_ENV=production`, `DEMO_MODE=false`, `MONGODB_URI`, `JWT_SECRET`, `INTERNAL_TASK_SECRET`, `GOOGLE_CLOUD_PROJECT`, `GCS_BUCKET`. Load secrets from Secret Manager, not the container image.

Do not run `gcloud run deploy` unless asked.

## Maps

Browser key only (`VITE_GOOGLE_MAPS_API_KEY`). Restrict by HTTP referrer and APIs (`Maps JavaScript API`, `Places API`). If the key is missing or blocked, the UI uses Leaflet and OpenStreetMap.

## Secret Manager

Store `JWT_SECRET`, `INTERNAL_TASK_SECRET`, `MONGODB_URI`, and `GEMINI_API_KEY` as secrets. Map them into Cloud Run as environment variables. Never mount a full JSON key into the frontend.

## BigQuery (required)

Set `REQUIRE_BIGQUERY=true` (default) and `BIGQUERY_DATASET` (e.g. `civicon_analytics`) in the same GCP project as `GOOGLE_CLOUD_PROJECT`.

The API creates the dataset/table if IAM allows, syncs each incident on create/status change, and powers **60-day recurrence** analytics on `/admin/analytics`. Enable `bigquery.googleapis.com` and grant the runtime identity `bigquery.dataEditor` + `bigquery.jobUser`.
