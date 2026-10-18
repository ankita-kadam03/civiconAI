# Civicon AI implementation audit

Workspace: `D:\Documents\civicon-ai`  
Spec: `CIVICON_AI_cursor_spec.md` (adapted from Next.js/Firestore to React/Vite + FastAPI + MongoDB)  
Date: 2026-10-18

This environment is **DEMO**. Civicon AI is not a government service.

## Existing project structure

```
civicon-ai/
  CIVICON_AI_cursor_spec.md
  README.md
  .env.example
  frontend/                 React + TypeScript + Vite + Tailwind
    src/app/                providers
    src/pages/              route screens (public, auth, citizen, admin)
    src/components/ui/      re-exports of shared UI
    src/components/layout/  re-exports of shell and guards
    src/features/auth/
    src/features/incidents/
    src/features/admin/
    src/features/notifications/
    src/features/community/
    src/features/maps/
    src/features/weather/
    src/features/chat/
    src/services/           API client re-export
    src/hooks/
    src/types/
    src/styles/
    src/lib/                canonical api, auth, types, schemas
  backend/                  Python FastAPI + PyMongo
    app/api/v1/             re-export of versioned router
    app/core/               settings and security re-exports
    app/models/             collection notes
    app/repositories/       Database re-export
    app/routers/            canonical HTTP routers (including v1)
    app/domain/             lifecycle, scoring, rbac, geo
    app/services/           scoring, community, weather, AI, GCS, Pub/Sub
    app/workers/            SLA and weather ticks
    app/integrations/       AI / storage / pubsub re-exports
    app/jobs/               legacy escalate job
    tests/
  docs/
```

Canonical implementations stay in `app/routers`, `app/services`, `app/db.py`, and `frontend/src/lib`. Feature folders wrap those modules; they are not a second product.

A sibling folder at `C:\Users\ankit\Documents\civicon-ai` is a Next.js/Firestore reference only. Firestore is not used here.

## Spec checklist

| Spec section | Status | Location |
| --- | --- | --- |
| 3.1 lifecycle aliases | Implemented with aliases | `backend/app/domain/lifecycle.py`. API still stores legacy statuses (`SUBMITTED`…) and maps them for Journey Line / scoring. |
| Escalation as level, not a status | Partial | `escalation_level` is stored. Legacy `ESCALATED` status still exists for older transitions. |
| R1 unique-reporter threshold | Implemented | `backend/app/services/priority.py`, `reports` collection. Tested. |
| R2 life-safety override | Implemented | `domain/scoring.py` + electrical/flooding seed categories. Tested. |
| R3 SLA table | Implemented | `domain/scoring.py` `SLA_MINUTES`, `/internal/tick/sla`. Demo time scale supported. |
| R4 community dispute | Implemented | `services/community.py` `apply_r4`. Tested. |
| Priority formula + stored factors | Implemented | `priority_score`, stored on incident, shown in UI. |
| Clustering unique reporters | Implemented | Nearby same-group incidents within 24h. Individual tickets are kept (no silent merge). |
| Promote / currently better / verify | Implemented | `/api/v1/incidents/{id}/promote\|better\|verify` + incident detail UI. |
| Saved locations | Implemented | `/api/v1/me/saved-locations` + citizen dashboard. |
| Notification tabs, thread-per-incident, prefs | Implemented (poll) | `/api/v1/notifications`, `notify()` updates one thread per user+incident. Quiet-hours prefs stored. Live delivery is authenticated polling, not Firestore. |
| FCM push with limits | Stub | Token storage exists. Send/fan-out/quiet-hours push filtering is not verified. |
| Weather fusion + auto posts | Implemented in workers | `services/weather.py`, `/internal/tick/weather`. Open-Meteo fetch not re-run in this session. |
| L1 / L2 / L3 boards | Implemented | `frontend/src/features/admin/Boards.tsx`, routes `/officer`, `/l2`, `/l3`. |
| Journey Line | Implemented | `frontend/src/features/incidents/JourneyLine.tsx` |
| Report wizard + 112 copy | Implemented | `frontend/src/pages/citizen.tsx` `ReportPage` |
| Admin analytics + hotspots | Implemented | `backend/app/routers/admin.py`, `frontend/src/pages/admin.tsx` |
| Dedicated `JWT_SECRET` | Implemented | Production requires `JWT_SECRET`. Demo uses a demo-only key. Never uses `INTERNAL_TASK_SECRET`. Tested. |
| PWA, Tamil, offline queue | Not implemented | Out of this pass. |
| MongoDB Atlas | Unconfigured locally | Memory demo when `MONGODB_URI` is missing. |

## Tests run this session

Backend (`backend\.venv\Scripts\python -m pytest tests -q`): **27 passed**.

Frontend:

- `npm run typecheck`: passed
- `npm run lint`: 0 errors, 4 `react-hooks/exhaustive-deps` warnings (`maps.tsx`, `citizen.tsx`)
- `npm run test`: **4 passed**
- `npm run build`: passed

## Integrations (honest)

| Integration | Configured | Verified this session | Result |
| --- | --- | --- | --- |
| MongoDB | `MONGODB_URI` missing | Ping skipped | Memory demo |
| JWT | `JWT_SECRET` missing | Demo signing path tested | Demo-only key. Not production-ready. |
| GCS | `GCS_BUCKET` set | Not re-checked this session | Previously `bucket.reload()` OK |
| Pub/Sub | project + topic set | Not re-checked this session | Previously `get_topic` OK |
| ADC / GCP project | set | Not re-checked this session | Previously available |
| Gemini / Vertex | `GEMINI_API_KEY` empty | **No paid generate call** | Heuristic fallback remains |
| Maps browser key | frontend env set | Not visually re-confirmed | OSM/Leaflet fallback is implemented |
| FCM | web config present | No service worker / send | Unverified |
| Open-Meteo | URL set | Worker code present | Live forecast not called this session |
| Firestore | unused | — | Not a source of truth |

## Port 8000 and disk

- Drive C had about **0.15 GB** free. Drive D had about **83 GB** free. No files were deleted.
- Port **8000** is already occupied by PID **19584** (`python.exe` from the user Python install). Its `/health` response is the **older** `{"status":"ok","service":"civicon-api","demo":true}` payload, so it is **not** this workspace's current API. It was not terminated.
- This workspace's current API was started on **8001** for verification. Vite for this pass used **5174** with `VITE_API_BASE_URL=http://127.0.0.1:8001`.
- Default docs still say port 8000. Use 8001 (or another free port) until 8000 is this app.

## Remaining limitations

- Legacy ticket statuses remain the stored values; spec names are aliases.
- Clustering counts unique reporters across nearby incidents; tickets are not auto-merged.
- Notifications are polled (about 20s), not pushed live.
- FCM send, quiet-hours push hold, and 5-non-critical-pushes/hour are not implemented as device push.
- Exposure (schools/hospitals within 300m) is stored as 0 unless later Places data exists.
- No PWA, Tamil UI, or offline report queue.
- Browser verification of every role at mobile width may be partial if the local 5173 process is a previous frontend.
- Demo seed users exist only when `DEMO_SEED_CONFIRM=yes`.
