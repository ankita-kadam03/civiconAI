# Civicon AI

**Your Neighbourhood. Your Voice.**

Civicon is a civic issue reporting and escalation app. Citizens submit and track issues; officers and administrators manage reports and service levels.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind, React Router |
| API | Python 3.11+, FastAPI |
| Primary database | Firestore in production; optional in-memory database for local development |
| Authentication | Civicon email/password accounts with server-issued JWTs and role-based access |
| Maps, weather, AI | Google Maps Platform, Weather API, Gemini API or Vertex AI |
| Optional cloud integrations | Cloud Storage, BigQuery, Pub/Sub |

## Run locally

### 1. Prepare backend settings

Create `backend/.env` with at least:

```dotenv
APP_ENV=development
ALLOW_MEMORY_DB=true
FRESH_START=false
```

Memory mode is for local development only: data is lost when the API process restarts. For a persistent local database, configure Firestore as described in [Google Cloud setup](./docs/google-cloud.md).

### 2. Start the API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API docs: <http://127.0.0.1:8000/docs>
- Health: `GET /health`
- Readiness: `GET /ready`

### 3. Start the frontend

Create `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
# Optional for map and location-picker screens:
VITE_GOOGLE_MAPS_API_KEY=
```

Then run:

```powershell
cd frontend
npm ci --legacy-peer-deps
npm run dev
```

Open <http://localhost:5173>. A Google Maps browser key is needed for map features, but not to start the API. To use Gemini, weather, or other Google Cloud-backed features locally, follow the credential setup below.

## Google resources and credentials

**Configure settings and credentials before starting or deploying the API.** Civicon reads application settings from `backend/.env`; Google Cloud client libraries use Application Default Credentials (ADC). Locally, ADC can be set up with `gcloud auth application-default login`. On Cloud Run, attach a service account with least-privilege IAM roles and use Secret Manager for secrets. Do not put server secrets in frontend variables or commit `.env` files.

| Google resource | Configure | What Civicon uses it for | If it is not configured |
| --- | --- | --- | --- |
| Firestore | `FIREBASE_PROJECT_ID` (falls back to `GOOGLE_CLOUD_PROJECT`); local ADC or Cloud Run service account | Persistent production database for users, issues, and application data | If neither project ID is set, the API requires `ALLOW_MEMORY_DB=true`; memory data is temporary and unsuitable for production |
| Gemini API or Vertex AI | Backend `GEMINI_API_KEY`, **or** `GOOGLE_CLOUD_PROJECT` plus ADC/Vertex permissions; optional `GEMINI_MODEL` | AI issue classification and CiviChat responses | CiviChat uses its built-in fallback; with the default `REQUIRE_GEMINI=true`, AI classification is unavailable when Gemini cannot be reached |
| Google Maps Platform | `VITE_GOOGLE_MAPS_API_KEY` in `frontend/.env.local` or `.env.production`; enable Maps JavaScript API and Places if used | Browser maps and location selection/search | Map features do not load. This key is public in the built frontend: restrict it by website referrer and API |
| Google Weather API | Backend `GOOGLE_SERVER_API_KEY`; enable Weather API | Current conditions and weather alerts, including location-based CiviChat weather | Weather information is unavailable. Keep this server key separate from the browser Maps key |
| Cloud Storage | Backend `GCS_BUCKET`, project and ADC/IAM | Stores uploaded report attachments privately | The API falls back to local disk, which is not durable storage on Cloud Run |
| BigQuery | Backend `GOOGLE_CLOUD_PROJECT` and `BIGQUERY_DATASET`; dataset and IAM | Analytics copy of created and updated issues | Analytics sync is unavailable; by default readiness checks expect BigQuery unless `REQUIRE_BIGQUERY=false` |
| Pub/Sub | Backend `GOOGLE_CLOUD_PROJECT` and `PUBSUB_TOPIC_EVENTS` (default `incident-events`); publisher IAM | Best-effort issue-created and status-changed events for downstream consumers | Event publishing is disabled or fails without blocking the core reporting flow |
| Cloud Run | Deploy the API image and attach a runtime service account | Runs the FastAPI backend and accesses Google Cloud resources through ADC | Production API is not hosted |
| Firebase Hosting | Deploys the built frontend; `VITE_API_BASE_URL` points to Cloud Run | Serves the static web application over HTTPS | Frontend is not hosted there |

Google Cloud APIs, billing where applicable, credentials, and IAM permissions must be enabled/configured in the selected project for the corresponding integration to work.

### Production setup order

1. Select the Google Cloud/Firebase project; enable billing and only the APIs for services you plan to use.
2. Create the Firestore database, Storage bucket, BigQuery dataset, and Pub/Sub topic you intend to use. Create separate browser Maps and backend Weather keys.
3. Grant the Cloud Run service account access to those resources. Add backend secrets such as `JWT_SECRET`, `GEMINI_API_KEY` (if using an API key), and `GOOGLE_SERVER_API_KEY` to Secret Manager and make them available to Cloud Run.
4. Deploy the backend with its runtime settings and verify `/ready` and **Admin → Health → Integrations**.
5. Set `VITE_API_BASE_URL` and the restricted browser Maps key in `frontend/.env.production`, build the frontend, and deploy Hosting.

This order ensures cloud resources and credentials exist before the app tries to use them. It also ensures the frontend build points to the deployed API. For commands, IAM roles, and deployment details, see [Google Cloud deployment](./docs/google-cloud.md); for Hosting, browser-key restrictions, Weather API setup, and CORS, see [Firebase Hosting](./docs/firebase-hosting.md).

### Which environment gets which values?

- **Frontend build:** `VITE_API_BASE_URL`, `VITE_GOOGLE_MAPS_API_KEY`, and optional `VITE_DEFAULT_MAP_LAT` / `VITE_DEFAULT_MAP_LNG`. `VITE_*` values are compiled into public browser assets; never put secrets there.
- **Backend runtime:** Firestore, Gemini/Vertex, Weather API, Storage, BigQuery, and Pub/Sub settings. Keep API keys and `JWT_SECRET` server-side; in production, store secrets in Secret Manager and grant the Cloud Run service account access.
- **Local Google Cloud access:** run `gcloud auth application-default login` and set `GOOGLE_CLOUD_PROJECT` in `backend/.env`. Set `FIREBASE_PROJECT_ID` to a different Firestore project if needed; otherwise `GOOGLE_CLOUD_PROJECT` is also used for Firestore. Because a configured project selects Firestore, leave both project IDs unset to use the local in-memory database. Do not download or commit service-account key files.

The app uses Civicon's own email/password and JWT authentication; Firebase Authentication is not required. Firebase web configuration variables in the environment template are not needed for the core app and do not, by themselves, enable browser push notifications.

## Demo accounts

These shared accounts are intentionally available on the live demo. Do not use them for private or sensitive data.

| Email | Password | Role |
| --- | --- | --- |
| `l1.wardnorth@example.com` | `CiviconDemo1` | Ward North Officer (L1) |
| `l1.wardsouth@example.com` | `CiviconDemo1` | Ward South Officer (L1) |
| `l2.regional@example.com` | `CiviconDemo1` | Regional Admin (L2) |
| `l3.municipal@example.com` | `CiviconDemo1` | Municipal Admin (L3) |
| `citizen.one@example.com` | `CiviconDemo1` | Citizen |
| `citizen.two@example.com` | `CiviconDemo1` | Citizen |

Bootstrap accounts are created only when `SEED_BOOTSTRAP_USERS=yes` and `SEED_BOOTSTRAP_PASSWORD` is explicitly set. Optional email settings are available in [backend/app/config.py](./backend/app/config.py). This setup is for the public demo only; never reuse the shared demo password for real accounts or other environments.

## Validation

There is no configured `npm test` script or checked-in `backend/tests` suite at present. Available frontend checks:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```

Backend Python syntax and lint checks (from the repository root, after installing `backend/requirements.txt`):

```powershell
.\backend\.venv\Scripts\python.exe -m compileall backend\app
.\backend\.venv\Scripts\ruff.exe check backend\app
```

## Security and production

- Never commit `.env` files, API secrets, service-account keys, or production passwords.
- Restrict browser Maps keys by referrer and API; keep server keys separate.
- Use a strong `JWT_SECRET` in production. See [security guidance](./docs/security.md).
- Never set `FRESH_START=true` in production; it resets application data.
- Configure `CORS_ORIGINS` on the API with the exact deployed frontend origins.
- Backend deployment: [Google Cloud deployment](./docs/google-cloud.md).
- Frontend deployment: `npm run deploy:web` after configuring `frontend/.env.production`; see [Firebase Hosting](./docs/firebase-hosting.md).
- Production URL: <https://civiconai.web.app>. The API's CORS configuration must include this origin.
