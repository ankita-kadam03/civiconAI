# Civicon AI

**Your Neighbourhood. Your Voice.**

Civic issue reporting and escalation: citizens file neighbourhood problems, officers track resolution, administrators monitor service levels.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind, React Router |
| Backend | Python 3.11+ FastAPI (`/docs` Swagger UI) |
| Database | Cloud Firestore (`ALLOW_MEMORY_DB=true` only for local/tests) |
| Auth | JWT access + refresh, bcrypt, roles: `CITIZEN`, `OFFICER`, `ADMIN`, `ADMIN_L2`, `ADMIN_L3` |
| Maps & weather | Google Maps Platform (browser key + server Weather API key) |
| AI | Gemini / Vertex AI (classification) |

No Node/Express backend. No Supabase.

## Local setup

### Environment

Do not commit `.env` files. Copy from `.env.example`:

- `frontend/.env.local` — `VITE_*` only (public browser keys; restrict in GCP/Firebase)
- `backend/.env` — secrets and server config

### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If port 8000 is busy, pick another port and set `VITE_API_BASE_URL` to match.

- API docs: http://127.0.0.1:8000/docs  
- Health: `GET /health`  
- Readiness: `GET /ready`

Firestore locally: `gcloud auth application-default login` and `FIREBASE_PROJECT_ID` in `backend/.env`.

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

App: http://localhost:5173

### One-time empty database

Set `FRESH_START=true` once, restart API, then set `FRESH_START=false`.

Set `DEFAULT_MAP_LAT` / `DEFAULT_MAP_LNG` (or Vite map center) and `VITE_GOOGLE_MAPS_API_KEY` for maps.

## Configuration reference

**Frontend**

| Name | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | FastAPI origin (default `http://127.0.0.1:8000`) |
| `VITE_GOOGLE_MAPS_API_KEY` | Maps JavaScript + Places |
| `VITE_FIREBASE_*` | Optional FCM web push |
| `VITE_DEFAULT_MAP_LAT` / `LNG` | Default map center |

`NEXT_PUBLIC_*` aliases are supported via Vite `envPrefix`.

**Backend**

| Name | Purpose |
| --- | --- |
| `FIREBASE_PROJECT_ID` | Firestore project |
| `ALLOW_MEMORY_DB` | `true` = in-memory (local only); production `false` |
| `JWT_SECRET` | Token signing; empty OK for local dev; **required in production** (Secret Manager) |
| `INTERNAL_TASK_SECRET` | Scheduler / internal HTTP auth |
| `GOOGLE_CLOUD_PROJECT` | GCP project for Vertex, GCS, Pub/Sub |
| `GOOGLE_SERVER_API_KEY` | Google Weather API (server key) |
| `GEMINI_API_KEY` / Vertex ADC | AI classification |
| `GCS_BUCKET` | Private photos; empty → local `backend/uploads` |
| `BIGQUERY_DATASET` | Analytics warehouse |
| `CORS_ORIGINS` | Allowed frontend origins (required in production) |
| `FRESH_START` | `true` wipes data on startup — never in production |

## Integrations

| Service | Role |
| --- | --- |
| Firestore | System of record |
| Cloud Storage | Report attachments |
| Gemini / Vertex | AI classify + CiviChat |
| BigQuery | Analytics sync |
| Pub/Sub | Incident events (best-effort) |
| Google Maps | Map UI and location picker |
| Google Weather | Current conditions / alerts bar |
| Cloud Run | Production API container (`backend/Dockerfile`) |

Verify integration status: **Admin → Health** (when signed in as admin).

## Tests

```bash
backend\.venv\Scripts\python -m pytest backend/tests -q

cd frontend
npm run test
npm run typecheck
npm run build
```

Escalation job (local):

```bash
cd backend
python -m app.jobs.escalate
```

Production equivalent: Cloud Scheduler → `POST /internal/tasks/escalate` with `X-Civicon-Task: <INTERNAL_TASK_SECRET>`.

## Security

See `docs/security.md`. Restrict browser API keys by referrer. Rotate any credential exposed outside env files.

## Production deployment

See **`docs/google-cloud.md`** (Cloud Run, Secret Manager, IAM, CORS, frontend build).

Possible GCP charges: Cloud Run, Firestore, Storage, Vertex/Gemini, BigQuery, Pub/Sub, Maps Platform, Weather API.
