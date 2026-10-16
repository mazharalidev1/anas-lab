
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from diagnostics_server.db import get_db
from diagnostics_server.models import MetricSnapshot

router = APIRouter(prefix="/api/v1/hosts", tags=["hosts"])

STALE_AFTER_SECONDS = 90


@router.get("/status")
def host_status(
    stale_after_seconds: int = Query(
        default=STALE_AFTER_SECONDS, ge=30, le=3600
    ),
    db: Session = Depends(get_db),
) -> list[dict]:
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

    snapshots = db.scalars(statement).all()
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=stale_after_seconds)
    results = []

    for snapshot in snapshots:
        observed_at = snapshot.observed_at

        # SQLite may return naive timestamps; normalize them defensively.
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)

        age_seconds = max(0, int((now - observed_at).total_seconds()))
        is_stale = observed_at < cutoff

        results.append({
            "agent_id": snapshot.agent_id,
            "hostname": snapshot.hostname,
            "status": "stale" if is_stale else "reporting",
            "last_seen_at": observed_at,
            "age_seconds": age_seconds,
            "platform": snapshot.platform,
        })

    return results
