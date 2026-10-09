def collect_docker_status() -> dict:
    # Docker SDK/socket access remains optional and is not required by the agent.
    return {"supported": False, "reason": "not_implemented"}
