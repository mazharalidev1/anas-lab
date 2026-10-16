
import argparse
import json
import logging
import time

from diagnostics_agent.collectors import collect_system_snapshot
from diagnostics_agent.config import AgentSettings
from diagnostics_agent.transport.client import DiagnosticsClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("diagnostics_agent")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Anas Labs diagnostics agent"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once",
        action="store_true",
        help="Collect and submit one snapshot",
    )
    mode.add_argument(
        "--print-only",
        action="store_true",
        help="Print a snapshot without sending it",
    )
    mode.add_argument(
        "--interval",
        type=int,
        metavar="SECONDS",
        help="Continuously collect and submit snapshots at this interval",
    )

    args = parser.parse_args()

    if args.interval is not None and args.interval < 1:
        parser.error("--interval must be at least 1 second")

    settings = AgentSettings()

    if args.print_only:
        snapshot = collect_system_snapshot(settings.agent_id)
        print(json.dumps(snapshot, indent=2))
        return

    if not settings.agent_token:
        parser.error(
            "Set DIAGNOSTICS_AGENT_TOKEN or use --print-only"
        )

    client = DiagnosticsClient(
        settings.server_url,
        settings.agent_token,
        settings.request_timeout,
    )

    def collect_and_submit() -> None:
        try:
            snapshot = collect_system_snapshot(settings.agent_id)
            result = client.submit_snapshot(snapshot)
            logger.info("Snapshot submitted: %s", result)
        except Exception:
            logger.exception("Snapshot collection or submission failed")

    if args.interval is not None:
        logger.info(
            "Starting continuous monitoring; interval=%s seconds",
            args.interval,
        )

        # Run immediately, then wait between subsequent attempts.
        while True:
            started = time.monotonic()
            collect_and_submit()

            # Count the interval from the start of each cycle.
            remaining = args.interval - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)

    else:
        # Preserve the existing --once behavior.
        snapshot = collect_system_snapshot(settings.agent_id)
        result = client.submit_snapshot(snapshot)
        print(json.dumps(result, indent=2))
