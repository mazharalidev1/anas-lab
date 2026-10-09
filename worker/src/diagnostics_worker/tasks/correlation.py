from diagnostics_worker.celery_app import app
@app.task(name="diagnostics.correlation.evaluate")
def evaluate_correlation(event_ids: list[str]) -> dict:
    return {"status": "not_implemented", "event_ids": event_ids}
