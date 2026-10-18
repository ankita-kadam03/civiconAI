# Civicon AI

**Your Neighbourhood. Your Voice.**

A civic issue reporting and escalation platform. Citizens file neighbourhood problems, officers track and resolve them, and administrators keep service levels honest.

This workspace uses:

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, React Router
- **Backend:** Python 3.11+ FastAPI (`/docs` Swagger UI)
- **Database:** Cloud Firestore (in-memory only when `ALLOW_MEMORY_DB=true` for local tests)
- **Auth:** JWT access and refresh tokens, bcrypt password hashing, role-based access (`CITIZEN`, `OFFICER`, `ADMIN`, `ADMIN_L2`, `ADMIN_L3`)

There is no Node.js/Express backend and no Supabase database in this architecture.

## Local setup

### 1. Environment files

Do not commit `.env` files. Copy names from `.env.example` into:

- `frontend/.env.local` for Vite (`VITE_*` variables)
- `backend/.env` for FastAPI

Never put private keys in `VITE_*` variables. Browser map and Firebase web keys are public by design and must be restricted in Google Cloud / Firebase consoles.

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

If port 8000 is already taken by another process, bind this workspace to a free port instead (for example `--port 8001`) and set `VITE_API_BASE_URL` to match. Do not kill unknown processes.

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Health: `GET /health`  
Readiness: `GET /ready`

### 3. Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

### 4. Empty database (one-time)

Use `FRESH_START=true` once to wipe all collections, then set `FRESH_START=false` and restart so data persists between restarts.

Maps use **Google Maps only** (no Leaflet). Set `DEFAULT_MAP_LAT` / `DEFAULT_MAP_LNG` and a browser Maps key.

See `docs/GCP_OBSERVABILITY.md` for where to view Storage, Vertex, Pub/Sub, and Maps usage in Google Cloud Console.

## Required vs optional variables

**Frontend (safe to expose if restricted):**

| Name | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | FastAPI origin. Default `http://localhost:8000` |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript + Places (required for maps) |
| `VITE_FIREBASE_*` | Optional FCM web config |

`NEXT_PUBLIC_*` names are also accepted by Vite (`envPrefix`).

**Backend:**

| Name | Purpose |
| --- | --- |
| `FIREBASE_PROJECT_ID` | Firestore project (same as Firebase / GCP project) |
| `ALLOW_MEMORY_DB` | `true` for local in-memory DB; production uses Firestore |
| `JWT_SECRET` | Signing secret. Required in production |
| `INTERNAL_TASK_SECRET` | Scheduler / Pub/Sub push auth |
| `GOOGLE_CLOUD_PROJECT` | Vertex, GCS, Pub/Sub |
| `GEMINI_API_KEY` | Gemini Developer API. Empty uses Vertex when a project is configured |
| `GEMINI_MODEL` | Preferred model id |
| `GCS_BUCKET` | Private complaint photos. Empty uses `backend/uploads` |
| `PUBSUB_TOPIC_EVENTS` | Optional event topic |
| `FRESH_START` | `true` clears all data on API startup before seed |

## Integrations

| Service | How it is used | Local status to verify |
| --- | --- | --- |
| Firestore | Authoritative records | `FIREBASE_PROJECT_ID` + Application Default Credentials |
| Gemini / Vertex | Server-side classify + helper chat | Heuristic fallback if credentials fail |
| Cloud Storage | Private object storage | Local disk fallback |
| Pub/Sub | Best-effort events | App works if publish fails |
| Maps | Incident map and location picker | Google Maps JavaScript API |
| Open-Meteo | Optional weather near a pin | Public, no key |
| Cloud Run | Container in `backend/Dockerfile` | Not deployed unless you approve |

## Tests

```bash
# API
backend\.venv\Scripts\python -m pytest backend/tests -q

# Frontend
cd frontend
npm run test
npm run typecheck
npm run build
```

Local escalation job:

```bash
cd backend
python -m app.jobs.escalate
```

Scheduler equivalent: `POST /internal/tasks/escalate` with header `X-Civicon-Task: <INTERNAL_TASK_SECRET>`.

## Security notes

- Citizens cannot promote themselves.
- Public incident pages hide private addresses, internal notes and private attachments.
- AI suggestions are labelled and never auto-reject or merge reports.
- Do not log tokens, passwords or private keys.
- Restrict browser API keys by HTTP referrer in Google Cloud. Rotate any key or password that was exposed in chat or tickets.

## Cloud deployment

See `docs/google-cloud.md`. Do not deploy, enable extra APIs, or create billed resources without explicit approval.

Possible costs if enabled: Vertex/Gemini usage, Cloud Storage, Pub/Sub, Cloud Run, Maps Platform, Firebase.
