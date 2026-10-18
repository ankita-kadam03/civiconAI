# Implementation plan

Keep FastAPI + MongoDB + React/Vite. Do not introduce Firestore or Next.js.

Status after this session: **executed**. See `docs/IMPLEMENTATION_AUDIT.md` for honest results.

## Done

1. Spec lifecycle aliases, scoring R1–R4, SLA table, promote/verify/claim, saved locations, notification tabs and threading.
2. L1 kanban, L2 and L3 boards, Journey Line, 112 copy, citizen saved places.
3. `JWT_SECRET` is never `INTERNAL_TASK_SECRET`. Production requires `JWT_SECRET`.
4. Folder aliases under `app/api`, `app/core`, `app/features`, `frontend/src/features` wrapping canonical modules.
5. Tests: backend 27 passed; frontend typecheck, 4 vitest, production build.

## Remaining (documented, not blocking this pass)

- FCM device push and quiet-hours push hold
- PWA / Tamil / offline queue
- Places-based exposure factor
- Auto-merge of duplicate tickets (clustering counts unique reporters instead)
- Bind to port 8000 only when it is this workspace’s process
