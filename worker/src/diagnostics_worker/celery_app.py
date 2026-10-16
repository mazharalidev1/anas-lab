import os

from celery import Celery

url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
app = Celery("diagnostics_worker", broker=url, backend=url, include=["diagnostics_worker.tasks.correlation", "diagnostics_worker.tasks.incidents", "diagnostics_worker.tasks.cleanup"])
app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json")
