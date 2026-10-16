
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text

from diagnostics_worker.celery_app import app


def parse_retention_days(value: str | None) -> int:
    if value is None:
        value = "90"

    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "RETENTION_DAYS must be a positive integer"
        ) from exc

    if days < 1:
        raise ValueError("RETENTION_DAYS must be at least 1")

    return days


def parse_dry_run(value: str | None) -> bool:
    if value is None:
        value = "true"

    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    raise ValueError(
        "CLEANUP_DRY_RUN must be a boolean value"
    )


RETENTION_DAYS = parse_retention_days(
    os.getenv("RETENTION_DAYS")
)
CLEANUP_DRY_RUN = parse_dry_run(
    os.getenv("CLEANUP_DRY_RUN")
)


@app.task(name="diagnostics.cleanup.expired_data")
def cleanup_expired_data() -> dict:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required for metric cleanup"
        )

    cutoff = datetime.now(UTC) - timedelta(
        days=RETENTION_DAYS
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    try:
        with engine.begin() as connection:
            eligible_count = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM metric_snapshots
                    WHERE observed_at < :cutoff
                """),
                {"cutoff": cutoff},
            ).scalar_one()

            deleted_count = 0

            if not CLEANUP_DRY_RUN:
                result = connection.execute(
                    text("""
                        DELETE FROM metric_snapshots
                        WHERE observed_at < :cutoff
                    """),
                    {"cutoff": cutoff},
                )
                deleted_count = result.rowcount

        return {
            "status": (
                "dry_run"
                if CLEANUP_DRY_RUN
                else "completed"
            ),
            "retention_days": RETENTION_DAYS,
            "cutoff": cutoff.isoformat(),
            "eligible_count": eligible_count,
            "deleted_count": deleted_count,
        }
    finally:
        engine.dispose()
