# Zero Trust Architecture — System Reference

This document describes the architecture, data flow, and operational details for the Zero Trust Architecture system in this repository. It is intended as a concise reference for researchers, operators, and developers who want to understand how the components interact, how data moves through the system, and what failure modes and verification steps to watch for.

## 1. High-level summary

- Components: Backend (FastAPI), SQLite DB (SQLAlchemy), Event Collector, WebSocket manager, ML Engine (IsolationForest-based), Frontend (Next.js + React).
- Purpose: Collect system events, persist them, allow a "Training Mode" to collect labelled data for an anomaly detection model, then train the model and switch to Live Mode for online inference.
- Interfaces: REST API endpoints for control (start/stop/status), event ingestion (`/api/events`), and admin queries; WebSocket `/ws` for live event and session broadcasts; frontend UI to orchestrate training/live modes and show event streams.

## 2. Components and responsibilities

1. Backend API (FastAPI)
   - Routers:
     - `routers.training` — start/stop/status for training sessions; maintains `current_training_session` in-memory pointer (restored on startup when possible).
     - `routers.events` — accepts event ingestion (`POST /api/events/`), persists events to DB and broadcasts to clients; has `GET /api/events` and `GET /api/events/recent` for retrieval.
     - `routers.live` and `routers.admin` — live mode and admin functions (anomalies, trust score, etc.).
   - Startup tasks in `main.py`:
     - Initialize DB and load ML model.
     - Restore any active training session from DB (sets a lightweight pointer with session id).
     - Start background event collection.

2. Database (SQLite, SQLAlchemy)
   - Tables/models: `sessions`, `events`, `anomalies`, `training_data`.
   - Session lifecycle: a `Session` row is created when training starts (mode='training', is_active=True). On stop, `is_active` is set False and `end_time` is written.
   - Events link to sessions via `session_id` when training is active. Events can have `NULL` `session_id` in non-training runs.

3. Event Collector (`event_collector.py`)
   - Collects system telemetry (platform-specific). On each collected event, `handle_collected_event` (in `main.py`) is invoked.
   - Writes events to the DB in a thread (using `SessionLocal`), attaches current `session_id` when training pointer is present.
   - Broadcasts the stored event via `websocket_manager.broadcast_event`.

4. WebSocket Manager (`websocket_manager.py`)
   - Manages connected WebSocket clients and broadcast helpers:
     - `broadcast_event` — push events to clients (optionally tagging `mode: training`).
     - `broadcast_session_update` — notify clients of session start/stop/completion.
   - Frontend subscribes to `/ws` for live updates.

5. ML Engine (`ml_engine.py`)
   - Encapsulates training and prediction logic (IsolationForest-based in this project).
   - `train_model(training_data)` — consumes collected events, trains model, saves model/version in DB.
   - `predict_anomaly(event)` — used in Live Mode to score incoming events.

6. Frontend (Next.js)
   - UI components: `TrainingMode`, `LiveMode`, `Admin`, `EventLog`, `StatsPanel`.
   - API wrapper (`frontend/lib/api.ts`) provides `trainingAPI`, `eventsAPI`, `adminAPI`.
   - WebSocket client (`frontend/lib/websocket.ts`) maintains a reconnecting socket and exposes hooks `useWebSocket` and `useWebSocketMessage` for components to handle messages.
   - `NoReloadGuard` (client) prevents programmatic hard reloads during long-running training runs.

## 3. Data flow (step-by-step)

1. Event generation
   - The event collector captures an event and invokes the backend callback `handle_collected_event(event_data)`.

2. Persisting event
   - `handle_collected_event` runs a thread function `_write_event` which:
     - Resolves `current_training_session.id` (if present) and creates a DB `Event` with `session_id` or NULL.
     - Commits the event and refreshes it to get DB-assigned `id` and `timestamp`.

3. Broadcasting
   - After storing, the backend schedules `websocket_manager.broadcast_event(payload)` on the main loop to push the event to connected clients.

4. Frontend consumption
   - Frontend receives `event` messages via WebSocket and updates the UI (EventLog, Stats) when in Training Mode.
   - Frontend can also call REST endpoints to fetch historical events for a session (`GET /api/events?session_id=<id>`), or session status (`GET /api/train/status`).

5. Training lifecycle
   - Start: `POST /api/train/start` creates a `Session` row in DB, sets `current_training_session` in-memory, and broadcasts `session_update` with status `started`.
   - Collect: events received while `current_training_session` is set are associated with that session.
   - Stop: `POST /api/train/stop` resolves the DB session by id, marks it inactive, queries all events for that session, and passes them to `ml_engine.train_model`. On success, `model_version` is written to the session row and `session_update` broadcast with `completed` status.

## 4. Key invariants and assumptions

- Only one active training session should be considered the canonical trainer at a time. The code uses an in-memory pointer `routers.training.current_training_session` and relies on DB rows `is_active` flags.
- On backend restart, the code restores the most recent active training session (if any) into `current_training_session` using a lightweight pointer (SimpleNamespace with `id`). Event writes re-resolve the ORM instance when needed.
- Events must be JSON-serializable for REST responses; the endpoints sanitize `event_metadata` before returning.

## 5. Known failure modes and hardening suggestions

1. Multiple sessions left `is_active=True` in DB
   - Cause: abrupt process termination before `stop` completes, or crashes during earlier runs.
   - Symptom: frontend's `start` returns 400 "already active"; multiple DB rows with `is_active=1`.
   - Fixes:
     - Provide an application-level guard to deactivate older active sessions automatically when starting a new one (or prevent creation if another active exists).
     - Add an admin "force close" endpoint to deactivate sessions.

2. Detached ORM session on stop
   - Cause: `current_training_session` restored as a lightweight pointer; the stop handler must re-resolve the DB instance by id (the code already does this).
   - Suggestion: keep using re-resolution and close the DB session properly to avoid stale state.

3. Programmatic reloads interrupt long training runs
   - Cause: dev HMR or third-party scripts calling `window.location.reload()`.
   - Mitigation: `NoReloadGuard` suppresses programmatic reload calls. For production, use a production build to disable HMR.

4. API response validation failures
   - Example: mismatched Pydantic field names caused the events endpoint to error (fixed in codebase).
   - Preventive measure: unit tests for API response shapes and end-to-end checks that `GET /api/events` returns valid JSON for typical event payloads.

## 6. Operational and runbook notes

- Start/Stop the system (from repo root):

```bash
# Start services (backend + frontend)
./start.sh

# Stop services
./stop.sh

# Tail logs
tail -f logs/backend.log
tail -f logs/frontend.log
```

- Quick health checks:
  - Backend: `GET http://localhost:8000/health`
  - API docs: `http://localhost:8000/docs`
  - Frontend: `http://localhost:3000`

- Debugging tips:
  - If training `start` returns "already active": query `GET /api/train/status` to see `session_id` and `events_count`, then `GET /api/events?session_id=<id>` to verify event persistence.
  - If the frontend shows 0 events but DB has events: check `/api/events` and `logs/backend.log` for validation errors.

## 7. Verification & simple experiments

- Experiment A: Start training and confirm events attach
  1. `POST /api/train/start` → receives `session_id`.
  2. Generate events (via event collector or POST /api/events). Wait a minute.
  3. `GET /api/train/status` should show `events_count > 0` for the session id.
  4. `GET /api/events?session_id=<id>&limit=20` should return recent events for the session.

- Experiment B: Stop training and verify model saved
  1. `POST /api/train/stop` once enough events are collected.
  2. Verify the session row has `is_active = False` and `model_version` filled.
  3. Frontend should receive a `session_update` with `status: completed` and `model_trained: true`.

## 8. Suggestions for research paper sections (next steps)

- Background & motivation: Why event-based zero-trust and anomaly detection?
- Data collection & feature engineering: what fields from `event_metadata` are used as features.
- Model selection rationale: why IsolationForest; hyperparameters; training/validation approach.
- Evaluation plan: offline metrics (precision/recall), simulated anomalies, live A/B rollout strategy.
- Security & privacy considerations: data retention, PII in `event_metadata`, access controls.

## 9. References & further reading

- Scikit-Learn IsolationForest: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy docs: https://docs.sqlalchemy.org/

---

If you want, I can:
- Add diagrams (Mermaid or ASCII) to this markdown.
- Generate a full research-paper skeleton (sections, suggested figures, experiments) in the same folder.
- Add a brief README in `Research paper/` that lists experiments and tracked metrics.

Tell me which follow-up you'd like and I will create it next.  

(End of architecture reference)
