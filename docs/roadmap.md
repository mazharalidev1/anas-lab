# Roadmap

## Implemented

- [x] Monorepo structure and independent Python package metadata
- [x] Linux system snapshot collectors
- [x] Bearer-token protected metric ingestion
- [x] PostgreSQL snapshot persistence
- [x] Latest and historical metrics API endpoints
- [x] Host reporting status endpoint
- [x] Administrator sessions and login rate limiting
- [x] Initial health rules and incident endpoints
- [x] React dashboard
- [x] Celery worker and Beat services
- [x] Configurable retention cleanup with dry-run support

## Planned

- [ ] Alembic database migrations
- [ ] Automated integration tests against PostgreSQL and Redis
- [ ] Agent registration and heartbeat management
- [ ] Expanded historical metrics charts and analysis
- [ ] systemd and Docker service collectors
- [ ] Event ingestion and deterministic incident correlation
- [ ] Evidence packs and diagnostic reports
- [ ] Production deployment and operational hardening

## Known limitations

The incident-processing and correlation Celery tasks are registered scaffolds;
they currently return `not_implemented`. They do not yet perform incident
processing or event correlation.
