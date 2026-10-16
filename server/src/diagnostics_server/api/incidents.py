

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from diagnostics_server.db import get_db
from diagnostics_server.models import Incident

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("")
def list_incidents(
    status: str | None = Query(default=None, pattern="^(active|resolved)$"),
    agent_id: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(Incident)

    if status:
        statement = statement.where(Incident.status == status)

    if agent_id:
        statement = statement.where(Incident.agent_id == agent_id)

    statement = statement.order_by(Incident.started_at.desc()).limit(limit)
    incidents = db.scalars(statement).all()

    return [
        {
            "id": incident.id,
            "agent_id": incident.agent_id,
            "hostname": incident.hostname,
            "rule_key": incident.rule_key,
            "title": incident.title,
            "severity": incident.severity,
            "status": incident.status,
            "started_at": incident.started_at,
            "last_seen_at": incident.last_seen_at,
            "resolved_at": incident.resolved_at,
            "evidence": incident.evidence,
        }
        for incident in incidents
    ]


@router.get("/summary")
def incident_summary(db: Session = Depends(get_db)) -> dict:
    active = db.scalars(
        select(Incident).where(Incident.status == "active")
    ).all()

    return {
        "active": len(active),
        "critical": sum(i.severity == "critical" for i in active),
        "warning": sum(i.severity == "warning" for i in active),
    }
