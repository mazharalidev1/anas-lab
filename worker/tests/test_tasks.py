from diagnostics_worker.celery_app import app
from diagnostics_worker.tasks.cleanup import cleanup_expired_data
from diagnostics_worker.tasks.correlation import evaluate_correlation
from diagnostics_worker.tasks.incidents import process_incident


def test_cleanup_task_is_registered():
    assert "diagnostics.cleanup.expired_data" in app.tasks
    assert cleanup_expired_data.name == "diagnostics.cleanup.expired_data"


def test_incident_task_is_registered():
    assert "diagnostics.incidents.process" in app.tasks
    assert process_incident.name == "diagnostics.incidents.process"


def test_correlation_task_is_registered():
    assert "diagnostics.correlation.evaluate" in app.tasks
    assert evaluate_correlation.name == "diagnostics.correlation.evaluate"


def test_incident_task_reports_unimplemented_status():
    result = process_incident.run("incident-123")

    assert result == {
        "status": "not_implemented",
        "incident_id": "incident-123",
    }


def test_correlation_task_reports_unimplemented_status():
    result = evaluate_correlation.run(["event-1", "event-2"])

    assert result == {
        "status": "not_implemented",
        "event_ids": ["event-1", "event-2"],
    }
