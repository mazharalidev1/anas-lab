from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from diagnostics_server import models  # noqa: F401
from diagnostics_server.api.auth import (
    SESSION_COOKIE,
    require_admin,
)
from diagnostics_server.api.auth import (
    router as auth_router,
)
from diagnostics_server.api.health import router as health_router
from diagnostics_server.api.hosts import router as hosts_router
from diagnostics_server.api.incidents import router as incidents_router
from diagnostics_server.api.metrics import router as metrics_router
from diagnostics_server.config import settings
from diagnostics_server.db import Base, engine

app = FastAPI(
    title="Anas Labs Production Diagnostics API",
    version="0.1.0",
)

# Development scaffold only; use Alembic migrations before production.
Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(metrics_router)
app.include_router(incidents_router)
app.include_router(hosts_router)


PUBLIC_API_ROUTES = {
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    # Agent authentication is enforced by require_agent_token
    # inside the metric ingestion endpoint.
    ("POST", "/api/v1/metrics"),
}

CSRF_EXEMPT_ROUTES = {
    ("POST", "/api/v1/metrics"),
}

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def origin_is_trusted(origin: str | None) -> bool:
    if not origin:
        return False

    trusted_origins = {
        item.strip().rstrip("/")
        for item in settings.trusted_origins.split(",")
        if item.strip()
    }

    return origin.rstrip("/") in trusted_origins

@app.middleware("http")
async def protect_api_routes(request: Request, call_next):
    path = request.url.path
    method = request.method

    if not (path == "/api/v1" or path.startswith("/api/v1/")):
        return await call_next(request)

    if method == "OPTIONS":
        return await call_next(request)

    # CSRF protection for browser requests that change state.
    # Agent ingestion uses its own Bearer-token authentication.
    if (
        method in STATE_CHANGING_METHODS
        and (method, path) not in CSRF_EXEMPT_ROUTES
        and not origin_is_trusted(request.headers.get("origin"))
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "Untrusted or missing request origin"},
        )

    # Public endpoints still have to pass the Origin check above.
    if (method, path) in PUBLIC_API_ROUTES:
        return await call_next(request)

    try:
        require_admin(request.cookies.get(SESSION_COOKIE))
    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    return await call_next(request)
