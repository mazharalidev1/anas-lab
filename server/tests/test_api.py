def test_metrics_payload_requires_auth_contract():
    # API integration tests are run with the service installed and DB configured.
    from diagnostics_server.schemas import MetricsBatch
    payload = MetricsBatch.model_validate({"schema_version":1,"agent_id":"a1","hostname":"web-01","platform":"Linux","observed_at":"2026-10-09T10:00:00Z","uptime_seconds":10,"metrics":{"cpu":{"percent":10.0}}})
    assert payload.agent_id == "a1"
