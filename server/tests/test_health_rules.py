from datetime import UTC, datetime, timedelta

import pytest
from diagnostics_server.db import Base
from diagnostics_server.diagnostics.health_rules import evaluate_snapshot
from diagnostics_server.models import Incident, MetricSnapshot
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


def add_snapshot(db, index, cpu_percent=20.0, metrics=None):
    observed_at = datetime.now(UTC) + timedelta(seconds=index)

    if metrics is None:
        metrics = {"cpu": {"percent": cpu_percent}}

    snapshot = MetricSnapshot(
        agent_id="test-agent",
        hostname="test-host",
        platform="Linux",
        observed_at=observed_at,
        uptime_seconds=1000 + index,
        metrics=metrics,
    )

    db.add(snapshot)
    db.flush()

    evaluate_snapshot(db, snapshot)
    db.flush()

    return snapshot


def get_incidents(db):
    return db.scalars(select(Incident)).all()


def test_incident_requires_three_consecutive_high_readings(db):
    add_snapshot(db, 1, cpu_percent=96)
    add_snapshot(db, 2, cpu_percent=96)

    assert get_incidents(db) == []

    add_snapshot(db, 3, cpu_percent=96)

    incidents = get_incidents(db)

    assert len(incidents) == 1
    assert incidents[0].rule_key == "cpu_high"
    assert incidents[0].severity == "critical"
    assert incidents[0].status == "active"


def test_active_incident_is_updated_not_duplicated(db):
    add_snapshot(db, 1, cpu_percent=96)
    add_snapshot(db, 2, cpu_percent=96)
    add_snapshot(db, 3, cpu_percent=96)

    add_snapshot(db, 4, cpu_percent=98)

    incidents = get_incidents(db)

    assert len(incidents) == 1
    assert incidents[0].status == "active"
    assert incidents[0].severity == "critical"
    assert incidents[0].evidence["value"] == 98.0


def test_incident_resolves_after_three_recovery_readings(db):
    for index in range(1, 4):
        add_snapshot(db, index, cpu_percent=96)

    for index in range(4, 6):
        add_snapshot(db, index, cpu_percent=50)

        incident = get_incidents(db)[0]
        assert incident.status == "active"

    add_snapshot(db, 6, cpu_percent=50)

    incidents = get_incidents(db)

    assert len(incidents) == 1
    assert incidents[0].status == "resolved"
    assert incidents[0].resolved_at is not None


def test_missing_cpu_metric_does_not_create_incident(db):
    for index in range(1, 5):
        add_snapshot(
            db,
            index,
            metrics={"memory": {"used_percent": 40.0}},
        )

    assert get_incidents(db) == []


def test_missing_cpu_metric_does_not_resolve_active_incident(db):
    for index in range(1, 4):
        add_snapshot(db, index, cpu_percent=96)

    add_snapshot(
        db,
        4,
        metrics={"memory": {"used_percent": 40.0}},
    )

    incidents = get_incidents(db)

    assert len(incidents) == 1
    assert incidents[0].status == "active"