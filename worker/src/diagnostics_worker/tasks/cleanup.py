from diagnostics_worker.celery_app import app
@app.task(name="diagnostics.cleanup.expired_data")
def cleanup_expired_data() -> dict:
    return {"status": "not_implemented"}
