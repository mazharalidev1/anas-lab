
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from diagnostics_server.auth.dependencies import require_agent_token
from diagnostics_server.db import get_db
from diagnostics_server.diagnostics.health_rules import evaluate_snapshot
from diagnostics_server.models import MetricSnapshot
from diagnostics_server.schemas import MetricsBatch, MetricSnapshotRead

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def ingest_metrics(
    batch: MetricsBatch,
    _: None = Depends(require_agent_token),
    db: Session = Depends(get_db),
) -> dict:
    row = MetricSnapshot(
        agent_id=batch.agent_id,
        hostname=batch.hostname,
        platform=batch.platform,
        observed_at=batch.observed_at,
        uptime_seconds=batch.uptime_seconds,
        metrics=batch.metrics,
    )
    db.add(row)
    db.flush()

    evaluate_snapshot(db, row)

    db.commit()
    db.refresh(row)

    return {
        "accepted": True,
        "persisted": True,
        "snapshot_id": row.id,
    }


@router.get("/latest", response_model=list[MetricSnapshotRead])
def latest_metrics(
    db: Session = Depends(get_db),
) -> list[MetricSnapshot]:
    ranked = (
        select(
            MetricSnapshot.id.label("id"),
            func.row_number()
            .over(
                partition_by=MetricSnapshot.agent_id,
                order_by=(
                    MetricSnapshot.observed_at.desc(),
                    MetricSnapshot.id.desc(),
                ),
            )
            .label("position"),
        )
        .subquery()
    )

    statement = (
        select(MetricSnapshot)
        .join(ranked, ranked.c.id == MetricSnapshot.id)
        .where(ranked.c.position == 1)
        .order_by(MetricSnapshot.hostname.asc())
    )

    return list(db.scalars(statement).all())


@router.get("/history", response_model=list[MetricSnapshotRead])
def metrics_history(
    agent_id: str | None = Query(default=None, min_length=1, max_length=128),
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=500, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[MetricSnapshot]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    statement = select(MetricSnapshot).where(
        MetricSnapshot.observed_at >= cutoff
    )

    if agent_id:
        statement = statement.where(MetricSnapshot.agent_id == agent_id)

    statement = statement.order_by(
        MetricSnapshot.observed_at.desc(),
        MetricSnapshot.id.desc(),
    ).limit(limit)

    return list(db.scalars(statement).all())
