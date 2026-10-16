
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from diagnostics_server.models import Incident, MetricSnapshot

CONSECUTIVE_SAMPLES = 3

RULES = {
    "cpu_high": {
        "metric": "cpu",
        "field": "percent",
        "threshold": 90.0,
        "critical_threshold": 95.0,
        "title": "High CPU usage",
    },
    "memory_high": {
        "metric": "memory",
        "field": "used_percent",
        "threshold": 90.0,
        "critical_threshold": 95.0,
        "title": "High memory usage",
    },
    "disk_high": {
        "metric": "disk",
        "field": "used_percent",
        "threshold": 90.0,
        "critical_threshold": 95.0,
        "title": "Low disk space",
    },
}


def _get_metric_value(
    snapshot: MetricSnapshot,
    rule: dict,
) -> float | None:
    """Return a valid numeric metric value, or None if unavailable."""

    metrics = snapshot.metrics or {}
    metric_data = metrics.get(rule["metric"]) or {}

    if not isinstance(metric_data, dict):
        return None

    value = metric_data.get(rule["field"])

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    return float(value)


def _consecutive_count(
    db: Session,
    snapshot: MetricSnapshot,
    rule: dict,
    condition,
) -> int:
    """
    Count consecutive matching snapshots, starting with the current one.

    A missing metric or a non-matching reading breaks the sequence.
    The current snapshot must already have been flushed to the database.
    """

    recent_snapshots = db.scalars(
        select(MetricSnapshot)
        .where(MetricSnapshot.agent_id == snapshot.agent_id)
        .order_by(
            MetricSnapshot.observed_at.desc(),
            MetricSnapshot.id.desc(),
        )
        .limit(CONSECUTIVE_SAMPLES)
    ).all()

    count = 0

    for recent in recent_snapshots:
        value = _get_metric_value(recent, rule)

        if value is None or not condition(value):
            break

        count += 1

    return count


def _find_active_incident(
    db: Session,
    agent_id: str,
    rule_key: str,
) -> Incident | None:
    """Find the active incident for one agent and rule."""

    return db.scalar(
        select(Incident)
        .where(
            Incident.agent_id == agent_id,
            Incident.rule_key == rule_key,
            Incident.status == "active",
        )
        .order_by(Incident.id.desc())
        .limit(1)
    )


def evaluate_snapshot(
    db: Session,
    snapshot: MetricSnapshot,
) -> None:
    """Create, update, or resolve incidents using consecutive readings."""

    now = datetime.now(UTC)

    for rule_key, rule in RULES.items():
        value = _get_metric_value(snapshot, rule)

        # Missing metrics must not create or resolve incidents.
        if value is None:
            continue

        incident = _find_active_incident(
            db,
            snapshot.agent_id,
            rule_key,
        )

        if value >= rule["threshold"]:
            high_count = _consecutive_count(
                db,
                snapshot,
                rule,
                lambda reading, threshold=rule["threshold"]: reading >= threshold,
            )

            severity = (
                "critical"
                if value >= rule["critical_threshold"]
                else "warning"
            )

            evidence = {
                "metric": rule["metric"],
                "field": rule["field"],
                "value": value,
                "threshold": rule["threshold"],
                "critical_threshold": rule["critical_threshold"],
                "snapshot_id": snapshot.id,
                "observed_at": snapshot.observed_at.isoformat(),
                "consecutive_high_samples": high_count,
                "required_samples": CONSECUTIVE_SAMPLES,
            }

            if incident is None:
                # Wait for consecutive high readings before creating
                # a new incident.
                if high_count < CONSECUTIVE_SAMPLES:
                    continue

                incident = Incident(
                    agent_id=snapshot.agent_id,
                    hostname=snapshot.hostname,
                    rule_key=rule_key,
                    title=rule["title"],
                    severity=severity,
                    status="active",
                    started_at=now,
                    last_seen_at=now,
                    evidence=evidence,
                )
                db.add(incident)
            else:
                # Keep an existing incident active while the resource
                # remains above its warning threshold.
                incident.hostname = snapshot.hostname
                incident.severity = severity
                incident.last_seen_at = now
                incident.evidence = evidence

            continue

        # The current reading is below the warning threshold.
        # Only resolve an existing incident after consecutive recovery.
        if incident is None:
            continue

        recovery_count = _consecutive_count(
            db,
            snapshot,
            rule,
            lambda reading, threshold=rule["threshold"]: reading < threshold,
        )

        previous_evidence = incident.evidence or {}

        incident.evidence = {
            **previous_evidence,
            "last_value": value,
            "last_snapshot_id": snapshot.id,
            "last_observed_at": snapshot.observed_at.isoformat(),
            "consecutive_recovery_samples": recovery_count,
            "required_recovery_samples": CONSECUTIVE_SAMPLES,
        }

        if recovery_count >= CONSECUTIVE_SAMPLES:
            incident.status = "resolved"
            incident.resolved_at = now
