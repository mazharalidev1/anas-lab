import platform, socket, time
from datetime import datetime, timezone
import psutil
from diagnostics_agent.collectors.cpu import collect_cpu
from diagnostics_agent.collectors.disk import collect_disk
from diagnostics_agent.collectors.memory import collect_memory
from diagnostics_agent.collectors.network import collect_network
from diagnostics_agent.collectors.processes import collect_process_summary

def collect_system_snapshot(agent_id: str) -> dict:
    return {"schema_version": 1, "agent_id": agent_id, "hostname": socket.gethostname(), "platform": platform.platform(), "observed_at": datetime.now(timezone.utc).isoformat(), "uptime_seconds": max(0, int(time.time() - psutil.boot_time())), "metrics": {"cpu": collect_cpu(), "memory": collect_memory(), "disk": collect_disk(), "network": collect_network(), "processes": collect_process_summary()}}
