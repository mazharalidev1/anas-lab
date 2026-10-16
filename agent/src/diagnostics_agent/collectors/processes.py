import psutil


def collect_process_summary() -> dict:
    total = running = 0
    for p in psutil.process_iter(attrs=["status"]):
        total += 1
        if p.info.get("status") == psutil.STATUS_RUNNING: running += 1
    return {"total": total, "running": running}
