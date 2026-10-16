from diagnostics_worker.celery_app import app


@app.task(name="diagnostics.incidents.process")
def process_incident(incident_id: str) -> dict:
    return {"status": "not_implemented", "incident_id": incident_id}
