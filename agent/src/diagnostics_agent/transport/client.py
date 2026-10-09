import httpx
from diagnostics_agent.transport.protocol import MetricsBatch

class DiagnosticsClient:
    def __init__(self, base_url: str, token: str, timeout: float = 10.0):
        self.base_url, self.token, self.timeout = base_url.rstrip("/"), token, timeout

    def submit_snapshot(self, snapshot: dict) -> dict:
        batch = MetricsBatch.model_validate(snapshot)
        response = httpx.post(f"{self.base_url}/api/v1/metrics", json=batch.model_dump(mode="json"), headers={"Authorization": f"Bearer {self.token}"}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
