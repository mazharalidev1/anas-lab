# Anas Labs — Host Diagnostics

An open-source diagnostics platform for monitoring Linux hosts, collecting system metrics, and identifying potential health issues.

**Status:** Early development — v0.1.0. APIs and configuration may change.

## Features

- Linux agent for collecting CPU, memory, disk, network, system, and process metrics
- FastAPI backend with PostgreSQL persistence
- Authenticated agent-to-server metric ingestion
- Admin login and session-based dashboard authentication
- Host and metrics views in the React dashboard
- Health rules and incident-related API endpoints
- Redis-backed sessions and login rate limiting
- Celery worker and Beat services for background tasks
- Docker Compose development environment

Incident correlation and broader event/log analysis remain ongoing development areas.

## Project structure

- `agent/` — Linux metrics collector and HTTP transport
- `server/` — FastAPI API, authentication, and PostgreSQL persistence
- `worker/` — Celery background tasks
- `web/` — React and Vite dashboard
- `shared/` — Shared metrics schemas
- `docker/` — Dockerfiles and Compose configuration
- `docs/` — Architecture and roadmap

Each Python service has its own `pyproject.toml`.

## Requirements

- Python 3.12+
- Docker Engine and Docker Compose
- Node.js and npm for local dashboard development

## Local setup

Create your local environment file:

```bash
cp .env.example .env
```

Edit `.env` before starting the services. Set a strong random PostgreSQL password, a matching `DATABASE_URL`, an agent token, an administrator password hash, and a session secret. Keep `.env` private and never commit it.

Start the services:

```bash
docker compose --env-file .env -f docker/compose.yml up --build -d
```

Check the API:

```bash
curl -fsS http://127.0.0.1:8000/health
```

To inspect service status and logs:

```bash
docker compose --env-file .env -f docker/compose.yml ps
docker compose --env-file .env -f docker/compose.yml logs --tail=100 api worker beat
```

The local API is intended for development. Do not expose it publicly without configuring HTTPS, trusted origins, secure session cookies, and production secrets.

## Run the agent locally

Create and activate a virtual environment, then install the agent:

```bash
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Configure `DIAGNOSTICS_SERVER_URL`, `DIAGNOSTICS_AGENT_ID`, and `DIAGNOSTICS_AGENT_TOKEN` for your environment. The agent token must match the server's configured token.

Collect a snapshot without sending it:

```bash
python -m diagnostics_agent --print-only
```

Send a single snapshot:

```bash
python -m diagnostics_agent --once
```

## Dashboard development

```bash
cd web
npm ci
npm run dev
```

Configure the development environment and trusted origins as needed for your local setup.

## Tests and linting

Install the relevant Python packages and development dependencies for the services you want to test. Run the repository's test suite and Ruff checks from the project root:

```bash
python -m ruff check agent server shared worker
python -m pytest -q
```

Build the dashboard:

```bash
cd web
npm ci
npm run build
```

## Security notes

- Agents authenticate metric submissions with a bearer token.
- Protect administrator credentials and session secrets.
- Do not commit `.env` or share real credentials in logs or screenshots.
- Keep the API private unless production access controls and HTTPS are configured.
- Do not execute arbitrary shell commands on monitored hosts through the server.
- Treat collected system and process information as potentially sensitive.

## Roadmap

See `docs/roadmap.md` for planned work. The project is under active development; the current release is not a claim of production readiness.

## License

Apache-2.0. See `LICENSE`.
