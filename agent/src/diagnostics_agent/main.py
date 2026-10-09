import argparse, json
from diagnostics_agent.collectors import collect_system_snapshot
from diagnostics_agent.config import AgentSettings
from diagnostics_agent.transport.client import DiagnosticsClient

def main() -> None:
    parser = argparse.ArgumentParser(description="Anas Labs diagnostics agent")
    parser.add_argument("--once", action="store_true", help="Collect and submit one snapshot")
    parser.add_argument("--print-only", action="store_true", help="Print snapshot without sending")
    args = parser.parse_args()
    settings = AgentSettings()
    snapshot = collect_system_snapshot(settings.agent_id)
    if args.print_only:
        print(json.dumps(snapshot, indent=2)); return
    if not settings.agent_token: parser.error("Set DIAGNOSTICS_AGENT_TOKEN or use --print-only")
    result = DiagnosticsClient(settings.server_url, settings.agent_token, settings.request_timeout).submit_snapshot(snapshot)
    print(json.dumps(result, indent=2))
    if not args.once: parser.error("Only --once is supported in this initial release")
