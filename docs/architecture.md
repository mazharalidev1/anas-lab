# Architecture — v0.1.0

## Current data flow

1. The Linux agent collects a versioned host snapshot.
2. The agent submits the snapshot to the FastAPI server using a bearer token.
3. The server validates the payload and stores the snapshot in PostgreSQL.
4. Health rules evaluate snapshots and maintain incident records.
5. Authenticated dashboard endpoints expose the latest metrics, historical metrics,
   host reporting status, and incident information.
6. Redis stores administrator sessions and login-rate-limit state.
7. Celery worker and Beat services provide the background task infrastructure,
   including configurable metric retention cleanup.

## Main components

- `agent/` — Linux system metric collection and HTTP transport.
- `server/` — FastAPI endpoints, authentication, persistence, and health rules.
- `shared/` — Shared metrics data contracts.
- `worker/` — Celery background tasks.
- `web/` — React dashboard.
- `docker/` — Dockerfiles and local Compose environment.

## Design principles

- Keep the agent lightweight.
- Do not implement arbitrary remote shell execution.
- Treat metrics, events, logs, and diagnostic evidence as separate concepts.
- Keep diagnostic findings tied to observable evidence.
- Keep AI optional.

## Current limitations

- Database tables are initialized with SQLAlchemy metadata; Alembic migrations
  are still needed.
- Agent registration and heartbeat management are not implemented.
- Event ingestion and broader incident correlation remain under development.
- Production deployment hardening and automated integration testing remain future work.
