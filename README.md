# Anas Labs — Production Diagnostics

Open-source diagnostics for Linux hosts and self-hosted applications. The long-term goal is to correlate metrics, service events and logs into evidence-backed incident timelines.

**Status:** early development / v0.1 scaffold. Interfaces may change.

## Monorepo layout

- `agent/` — lightweight Linux metrics collector and HTTP transport
- `server/` — FastAPI ingestion API and PostgreSQL persistence
- `worker/` — Celery tasks for future event correlation and cleanup
- `web/` — React/Vite dashboard shell
- `shared/` — versioned data contract
- `docker/` — local development Compose configuration and Dockerfiles
- `docs/` — architecture and protocol notes

Each Python service has its own `pyproject.toml`.

## Start the backend

Requirements: Python 3.12+, Docker Compose. Copy `.env.example` to `.env`, then run:

```bash
docker compose -f docker/compose.yml up --build
curl http://127.0.0.1:8000/health
```

The API is bound to localhost for development. Replace development secrets before any deployment.

## Run the agent locally

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
DIAGNOSTICS_SERVER_URL=http://127.0.0.1:8000 DIAGNOSTICS_AGENT_ID=dev-host DIAGNOSTICS_AGENT_TOKEN=change-this-agent-token python -m diagnostics_agent --once
```

Use `python -m diagnostics_agent --print-only` to collect a snapshot without sending it.

## Tests

```bash
pip install -e 'server/.[dev]'
pip install -e 'agent/.[dev]'
pytest server/tests agent/tests
```

## Security

- The agent authenticates with a bearer token.
- Do not expose this development API publicly.
- Never send arbitrary shell commands from the server to an agent.
- Log collection is not enabled in this scaffold because logs can contain secrets.

## License

Apache-2.0. See `LICENSE`.
