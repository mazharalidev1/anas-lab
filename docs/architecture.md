# Architecture — v0.1

1. Agent collects a versioned host snapshot.
2. Agent submits JSON over HTTP(S).
3. API authenticates the bearer token and validates payloads.
4. API persists snapshots in PostgreSQL.
5. Future releases add historical queries, event correlation, incident evidence and UI charts.

Principles: lightweight agent; no arbitrary remote shell commands; metrics, events, logs and evidence are separate concepts; diagnostic findings must cite evidence; AI remains optional.
