
import os

# Must be set before importing diagnostics_server modules.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AGENT_TOKEN"] = "test-agent-token"

from datetime import UTC, datetime, timedelta

import pytest
from diagnostics_server.api import auth as auth_module
from diagnostics_server.api.auth import SESSION_COOKIE, serializer
from diagnostics_server.config import settings
from diagnostics_server.db import Base, get_db
from diagnostics_server.main import app
from diagnostics_server.models import Incident
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client(monkeypatch):
    # An isolated in-memory database for every test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(settings, "agent_token", "test-agent-token")
    monkeypatch.setattr(auth_module, "reserve_login_attempt", lambda ip: None)
    monkeypatch.setattr(auth_module, "release_login_attempt", lambda ip: None)

    # Keep authentication tests independent of a running Redis instance.
    monkeypatch.setattr(auth_module, "register_session", lambda session_id: None)
    monkeypatch.setattr(auth_module, "session_is_active", lambda session_id: True)
    monkeypatch.setattr(auth_module, "revoke_session", lambda session_id: None)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, headers={"Origin": "https://anas-lab.test"}) as test_client:
        test_client.cookies.set(
            SESSION_COOKIE,
            serializer.dumps({
                "sub": settings.admin_username,
                "jti": "test-session",
            }),
        )
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def payload(
    agent_id="agent-test",
    hostname="test-host",
    observed_at=None,
    cpu_percent=20.0,
):
    return {
        "schema_version": 1,
        "agent_id": agent_id,
        "hostname": hostname,
        "platform": "Linux",
        "observed_at": (
            observed_at or datetime.now(UTC)
        ).isoformat(),
        "uptime_seconds": 3600,
        "metrics": {
            "cpu": {"percent": cpu_percent},
            "memory": {"used_percent": 40.0},
            "disk": {"used_percent": 50.0},
        },
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer wrong-token", "wrong-token"],
)
def test_metrics_ingestion_rejects_invalid_auth(client, authorization):
    headers = {}
    if authorization is not None:
        headers["Authorization"] = authorization

    response = client.post(
        "/api/v1/metrics",
        json=payload(),
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid agent token"


def test_metrics_ingestion_persists_snapshot(client):
    response = client.post(
        "/api/v1/metrics",
        json=payload(),
        headers={"Authorization": "Bearer test-agent-token"},
    )

    assert response.status_code == 202

    body = response.json()
    assert body["accepted"] is True
    assert body["persisted"] is True
    assert isinstance(body["snapshot_id"], int)


def test_latest_metrics_returns_latest_snapshot_per_agent(client):
    headers = {"Authorization": "Bearer test-agent-token"}
    now = datetime.now(UTC)

    for timestamp, cpu in [
        (now - timedelta(minutes=2), 25.0),
        (now - timedelta(minutes=1), 55.0),
    ]:
        response = client.post(
            "/api/v1/metrics",
            json=payload(
                observed_at=timestamp,
                cpu_percent=cpu,
            ),
            headers=headers,
        )
        assert response.status_code == 202

    response = client.get("/api/v1/metrics/latest")

    assert response.status_code == 200
    rows = response.json()

    assert len(rows) == 1
    assert rows[0]["agent_id"] == "agent-test"
    assert rows[0]["metrics"]["cpu"]["percent"] == 55.0


def test_latest_metrics_returns_one_snapshot_per_agent(client):
    headers = {"Authorization": "Bearer test-agent-token"}

    for agent_id, hostname in [
        ("agent-a", "host-a"),
        ("agent-b", "host-b"),
    ]:
        response = client.post(
            "/api/v1/metrics",
            json=payload(agent_id=agent_id, hostname=hostname),
            headers=headers,
        )
        assert response.status_code == 202

    response = client.get("/api/v1/metrics/latest")

    assert response.status_code == 200
    assert {row["agent_id"] for row in response.json()} == {
        "agent-a",
        "agent-b",
    }


def test_metrics_history_filters_by_agent(client):
    headers = {"Authorization": "Bearer test-agent-token"}
    now = datetime.now(UTC)

    for agent_id, hostname in [
        ("agent-a", "host-a"),
        ("agent-b", "host-b"),
    ]:
        response = client.post(
            "/api/v1/metrics",
            json=payload(
                agent_id=agent_id,
                hostname=hostname,
                observed_at=now,
            ),
            headers=headers,
        )
        assert response.status_code == 202

    response = client.get(
        "/api/v1/metrics/history",
        params={"agent_id": "agent-a", "hours": 24},
    )

    assert response.status_code == 200
    rows = response.json()

    assert len(rows) == 1
    assert rows[0]["agent_id"] == "agent-a"


def test_metrics_history_rejects_invalid_hours(client):
    response = client.get(
        "/api/v1/metrics/history",
        params={"hours": 0},
    )

    assert response.status_code == 422



def seed_snapshot(
    client,
    agent_id,
    hostname,
    observed_at,
):
    response = client.post(
        "/api/v1/metrics",
        json=payload(
            agent_id=agent_id,
            hostname=hostname,
            observed_at=observed_at,
        ),
        headers={"Authorization": "Bearer test-agent-token"},
    )
    assert response.status_code == 202
    return response.json()["snapshot_id"]


def seed_incident(
    client,
    agent_id="agent-test",
    hostname="test-host",
    rule_key="cpu_high",
    severity="warning",
    status="active",
    started_at=None,
):
    # Insert directly into the isolated test database.
    from diagnostics_server.db import get_db

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    now = datetime.now(UTC)
    incident = Incident(
        agent_id=agent_id,
        hostname=hostname,
        rule_key=rule_key,
        title="High CPU usage",
        severity=severity,
        status=status,
        started_at=started_at or now,
        last_seen_at=now,
        resolved_at=now if status == "resolved" else None,
        evidence={"value": 96.0, "threshold": 90.0},
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)
    incident_id = incident.id

    try:
        db.close()
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass

    return incident_id


def test_host_status_returns_reporting_host(client):
    now = datetime.now(UTC)

    seed_snapshot(
        client,
        "agent-a",
        "web-01",
        now - timedelta(seconds=10),
    )

    response = client.get("/api/v1/hosts/status")

    assert response.status_code == 200
    hosts = response.json()

    assert len(hosts) == 1
    assert hosts[0]["agent_id"] == "agent-a"
    assert hosts[0]["hostname"] == "web-01"
    assert hosts[0]["status"] == "reporting"


def test_host_status_marks_old_snapshot_stale(client):
    now = datetime.now(UTC)

    seed_snapshot(
        client,
        "agent-old",
        "old-host",
        now - timedelta(minutes=10),
    )

    response = client.get(
        "/api/v1/hosts/status",
        params={"stale_after_seconds": 90},
    )

    assert response.status_code == 200
    assert response.json()[0]["status"] == "stale"


def test_host_status_rejects_invalid_stale_threshold(client):
    response = client.get(
        "/api/v1/hosts/status",
        params={"stale_after_seconds": 10},
    )

    assert response.status_code == 422



def test_incident_list_filters_by_status_and_agent(client):
    seed_incident(
        client,
        agent_id="agent-a",
        status="active",
        severity="critical",
    )
    seed_incident(
        client,
        agent_id="agent-b",
        status="resolved",
        severity="warning",
    )

    response = client.get(
        "/api/v1/incidents",
        params={"status": "active", "agent_id": "agent-a"},
    )

    assert response.status_code == 200
    incidents = response.json()

    assert len(incidents) == 1
    assert incidents[0]["agent_id"] == "agent-a"
    assert incidents[0]["status"] == "active"
    assert incidents[0]["severity"] == "critical"


def test_incident_summary_counts_active_severities(client):
    seed_incident(
        client,
        agent_id="agent-a",
        severity="critical",
        status="active",
    )
    seed_incident(
        client,
        agent_id="agent-b",
        severity="warning",
        status="active",
    )
    seed_incident(
        client,
        agent_id="agent-c",
        severity="warning",
        status="resolved",
    )

    response = client.get("/api/v1/incidents/summary")

    assert response.status_code == 200
    assert response.json() == {
        "active": 2,
        "critical": 1,
        "warning": 1,
    }


def test_incident_list_rejects_invalid_status(client):
    response = client.get(
        "/api/v1/incidents",
        params={"status": "pending"},
    )

    assert response.status_code == 422



def test_dashboard_reads_require_admin_session(client):
    client.cookies.delete(SESSION_COOKIE)

    for path in (
        "/api/v1/auth/me",
        "/api/v1/metrics/latest",
        "/api/v1/metrics/history",
        "/api/v1/hosts/status",
        "/api/v1/incidents",
        "/api/v1/incidents/summary",
    ):
        response = client.get(path)
        assert response.status_code == 401, (path, response.status_code)


def test_login_sets_http_only_session_cookie(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "test-admin")
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        auth_module.password_hasher.hash("test-password"),
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "test-password"},
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] == "true"
    assert SESSION_COOKIE in response.cookies
    assert "httponly" in response.headers.get("set-cookie", "").lower()


def test_login_rejects_invalid_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "test-admin")
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        auth_module.password_hasher.hash("test-password"),
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_rate_limit_returns_429(client, monkeypatch):
    attempts = {"reserved": 0}

    def reserve_attempt(_ip):
        if attempts["reserved"] >= 5:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Try again later.",
            )
        attempts["reserved"] += 1

    def release_attempt(_ip):
        attempts["reserved"] = max(0, attempts["reserved"] - 1)

    monkeypatch.setattr(auth_module, "reserve_login_attempt", reserve_attempt)
    monkeypatch.setattr(auth_module, "release_login_attempt", release_attempt)
    monkeypatch.setattr(settings, "admin_username", "test-admin")
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        auth_module.password_hasher.hash("test-password"),
    )

    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-admin", "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "test-password"},
    )
    assert response.status_code == 429


def test_logout_clears_session_cookie(client):
    # Confirm the initial session is valid.
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200

    # Log out and verify that the response expires the cookie.
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    set_cookie = response.headers.get("set-cookie", "").lower()
    assert SESSION_COOKIE.lower() in set_cookie
    assert "max-age=0" in set_cookie or "expires=" in set_cookie

    # Explicitly remove the cookie from the test client's cookie jar.
    client.cookies.delete(SESSION_COOKIE)

    # Dashboard access must now be rejected.
    response = client.get("/api/v1/metrics/latest")
    assert response.status_code == 401


def test_agent_ingestion_still_requires_bearer_token(client):
    response = client.post("/api/v1/metrics", json=payload())
    assert response.status_code == 401

    response = client.post(
        "/api/v1/metrics",
        json=payload(),
        headers={"Authorization": "Bearer test-agent-token"},
    )
    assert response.status_code == 202


def test_logout_revokes_server_side_session(client, monkeypatch):
    revoked = []

    monkeypatch.setattr(
        auth_module,
        "revoke_session",
        lambda session_id: revoked.append(session_id),
    )

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert revoked == ["test-session"]


def test_login_rejects_untrusted_origin(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "anything"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Untrusted or missing request origin"
    )


def test_login_rejects_missing_origin(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "anything"},
        headers={"Origin": ""},
    )

    assert response.status_code == 403


def test_agent_ingestion_does_not_require_origin(client):
    response = client.post(
        "/api/v1/metrics",
        json=payload(),
        headers={
            "Authorization": "Bearer test-agent-token",
            "Origin": "",
        },
    )

    assert response.status_code == 202


def test_expired_session_cannot_access_dashboard(client, monkeypatch):
    from diagnostics_server.api import auth as auth_module

    # Force the session age limit to be negative for this test.
    monkeypatch.setattr(auth_module, "SESSION_TTL_SECONDS", -1)

    expired_cookie = auth_module.serializer.dumps(
        {
            "sub": auth_module.settings.admin_username,
            "jti": "expired-test-session",
        }
    )

    client.cookies.set(auth_module.SESSION_COOKIE, expired_cookie)

    response = client.get("/api/v1/metrics/latest")

    assert response.status_code == 401


def test_revoked_session_cannot_access_dashboard(client, monkeypatch):
    from diagnostics_server.api import auth as auth_module

    # Simulate Redis reporting that the session was revoked.
    monkeypatch.setattr(
        auth_module,
        "session_is_active",
        lambda session_id: False,
    )

    response = client.get("/api/v1/metrics/latest")

    assert response.status_code == 401

def test_redis_unavailable_blocks_dashboard_access(client, monkeypatch):
    from fastapi import HTTPException
    from starlette import status

    def redis_unavailable(_session_id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session service is temporarily unavailable",
        )

    monkeypatch.setattr(
        auth_module,
        "session_is_active",
        redis_unavailable,
    )

    response = client.get("/api/v1/metrics/latest")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Session service is temporarily unavailable"
    )



def test_login_returns_503_when_redis_unavailable(client, monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "admin_username", "test-admin")
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        auth_module.password_hasher.hash("test-password"),
    )

    def redis_unavailable(_session_id):
        raise HTTPException(
            status_code=503,
            detail="Session service is temporarily unavailable",
            headers={"Retry-After": "30"},
        )

    monkeypatch.setattr(
        auth_module,
        "register_session",
        redis_unavailable,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "test-admin",
            "password": "test-password",
        },
    )

    assert response.status_code == 503
    assert "anas_admin_session" not in response.headers.get(
        "set-cookie", ""
    )

def test_logout_returns_503_when_redis_unavailable(client, monkeypatch):
    from fastapi import HTTPException

    def redis_unavailable(_session_id):
        raise HTTPException(
            status_code=503,
            detail="Session service is temporarily unavailable",
        )

    monkeypatch.setattr(
        auth_module,
        "revoke_session",
        redis_unavailable,
    )

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 503
    assert response.json()["authenticated"] == "false"
    assert "anas_admin_session" in response.headers.get(
        "set-cookie", ""
    )
