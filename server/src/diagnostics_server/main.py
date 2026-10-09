from fastapi import FastAPI
from diagnostics_server import models  # noqa: F401
from diagnostics_server.api.health import router as health_router
from diagnostics_server.api.metrics import router as metrics_router
from diagnostics_server.db import Base, engine
app = FastAPI(title="Anas Labs Production Diagnostics API", version="0.1.0")
# Development scaffold only; use Alembic migrations before production.
Base.metadata.create_all(bind=engine)
app.include_router(health_router)
app.include_router(metrics_router)
