# Google Cloud — Civicon AI

Production target: **Cloud Run** (`civicon-api`) in your GCP/Firebase project, with **Firestore**, **Cloud Storage**, **Gemini/Vertex**, **BigQuery**, **Maps Platform**, and **Weather API**.

## Authentication

**Local:** Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Production:** Cloud Run service account (no JSON key files in the repo or container).

## Cloud Run (API)

Image: `backend/Dockerfile` → `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`.

Suggested service name: **`civicon-api`**. Region: e.g. **`asia-south1`**.

**Required env (examples):**

| Variable | Notes |
| --- | --- |
| `APP_ENV` | `production` |
| `ALLOW_MEMORY_DB` | `false` |
| `FIREBASE_PROJECT_ID` | Same as Firebase/GCP project |
| `GOOGLE_CLOUD_PROJECT` | Vertex, GCS, Pub/Sub |
| `GCS_BUCKET` | Private photo bucket |
| `BIGQUERY_DATASET` | e.g. `civicon_analytics` |
| `CORS_ORIGINS` | HTTPS frontend origin(s), comma-separated |
| `JWT_SECRET` | From Secret Manager (see below) |
| `INTERNAL_TASK_SECRET` | Scheduler / internal routes |
| `GOOGLE_SERVER_API_KEY` | Weather API (server key, not browser Maps key) |

Mount secrets via **Secret Manager** → Cloud Run **Variables & secrets** (e.g. `civicon-jwt-secret` → `JWT_SECRET`).

Do not set `FRESH_START=true` in production unless you intend to wipe data.

The container listens on **`PORT`** (Cloud Run sets **8080**). By default the API **starts even if** Vertex/BigQuery are misconfigured; check **`GET /ready`** for `integration_issues`. Set `FAIL_STARTUP_ON_INTEGRATIONS=true` only after IAM is complete if you want a hard fail on missing Gemini/BigQuery.

**Frontend:** Build Vite with `VITE_API_BASE_URL=https://YOUR-civicon-api-....run.app`. Deploy static assets via **Firebase Hosting** or a separate Cloud Run static service. Restrict `VITE_GOOGLE_MAPS_API_KEY` by HTTP referrer on the live domain.

## Secret Manager

Store at minimum:

- `JWT_SECRET` (secret name e.g. `civicon-jwt-secret`)
- `INTERNAL_TASK_SECRET`
- Optional: `GEMINI_API_KEY`, `GOOGLE_SERVER_API_KEY`

Grant the Cloud Run runtime service account **`roles/secretmanager.secretAccessor`** on those secrets.

### JWT

Civicon uses **server-issued JWT** for API auth (email/password). Use a random 32+ character secret; never commit it. **Admin → Health → auth** should show `ok` when configured.

## Vertex AI / Gemini

Default `REQUIRE_GEMINI=true`. Configure **either** `GEMINI_API_KEY` **or** `GOOGLE_CLOUD_PROJECT` + Vertex ADC.

Enable `generativelanguage.googleapis.com` and/or `aiplatform.googleapis.com`. Classification returns **503** when Gemini is required but unavailable.

## Cloud Storage

Private bucket (`GCS_BUCKET`). Runtime needs `storage.objects.create` and `storage.objects.get`. Objects are not public; the API streams after auth.

## Firestore

Primary database when `ALLOW_MEMORY_DB=false` and `FIREBASE_PROJECT_ID` is set. Runtime needs Firestore access (e.g. `roles/datastore.user`).

## BigQuery

Set `REQUIRE_BIGQUERY=true` (default) and `BIGQUERY_DATASET`. Enable `bigquery.googleapis.com`; grant `bigquery.dataEditor` and `bigquery.jobUser`.

## Pub/Sub

Topic: `PUBSUB_TOPIC_EVENTS` (default `incident-events`). Push to `POST /internal/events` with `INTERNAL_TASK_SECRET` (or OIDC via `PUSH_SERVICE_ACCOUNT` / `INTERNAL_OIDC_AUDIENCE`). Publish failures are non-fatal.

## Cloud Scheduler

Periodic `POST /internal/tasks/escalate` with header `X-Civicon-Task: <INTERNAL_TASK_SECRET>`. Local equivalent: `python -m app.jobs.escalate` from `backend/`.

## Maps (browser)

`VITE_GOOGLE_MAPS_API_KEY` only in the frontend. Restrict by **HTTP referrer** and APIs: Maps JavaScript API, Places. Maps require a valid key; there is no third-party map fallback in production UI.

## Weather (server)

Enable **Weather API** (`weather.googleapis.com`). Set **`GOOGLE_SERVER_API_KEY`** on the backend. Do not reuse the browser Maps key (referrer restrictions block server calls).

## Observability in Console

| Area | Where in GCP Console |
| --- | --- |
| Cloud Run logs & metrics | Cloud Run → `civicon-api` → Logs / Metrics |
| Firestore usage | Firestore → Usage |
| Storage | Cloud Storage → bucket metrics |
| Vertex / Gemini | Vertex AI → Dashboard / Generative AI |
| BigQuery | BigQuery → job history |
| Pub/Sub | Pub/Sub → Topics → metrics |
| Maps & Weather quotas | APIs & Services → Enabled APIs → quotas |
| Secret access | Secret Manager → secret → Permissions / audit |

## IAM (runtime service account)

Typical roles for the Cloud Run identity:

- `roles/datastore.user`
- `roles/storage.objectAdmin` (or tighter bucket-level)
- `roles/aiplatform.user` (if using Vertex)
- `roles/pubsub.publisher`
- `roles/bigquery.dataEditor`, `roles/bigquery.jobUser`
- `roles/secretmanager.secretAccessor` (on app secrets)
- FCM: as needed for push (`firebasecloudmessaging` admin or equivalent)

Adjust to least privilege for your org.
