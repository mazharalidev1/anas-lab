import psutil


def collect_memory() -> dict:
    m = psutil.virtual_memory()
    return {"total_bytes": m.total, "available_bytes": m.available, "used_bytes": m.used, "used_percent": m.percent}
