from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from diagnostics_server.auth.dependencies import require_agent_token
from diagnostics_server.db import get_db
from diagnostics_server.models import MetricSnapshot
from diagnostics_server.schemas import MetricsBatch
router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"], dependencies=[Depends(require_agent_token)])
@router.post("", status_code=status.HTTP_202_ACCEPTED)
def ingest_metrics(batch: MetricsBatch, db: Session = Depends(get_db)) -> dict:
    row = MetricSnapshot(agent_id=batch.agent_id, hostname=batch.hostname, platform=batch.platform, observed_at=batch.observed_at, uptime_seconds=batch.uptime_seconds, metrics=batch.metrics)
    db.add(row); db.commit(); db.refresh(row)
    return {"accepted": True, "persisted": True, "snapshot_id": row.id}
