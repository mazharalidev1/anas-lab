from diagnostics_agent.collectors import collect_system_snapshot

def test_snapshot_shape():
    s = collect_system_snapshot("test-agent")
    assert s["schema_version"] == 1 and s["agent_id"] == "test-agent"
    assert s["hostname"] and s["observed_at"] and s["uptime_seconds"] >= 0
    assert 0 <= s["metrics"]["memory"]["used_percent"] <= 100
