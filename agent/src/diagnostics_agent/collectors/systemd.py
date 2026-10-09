def collect_systemd_status() -> dict:
    # Read-only systemd collection will be implemented in a later milestone.
    return {"supported": False, "reason": "not_implemented"}
