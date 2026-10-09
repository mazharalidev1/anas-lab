import psutil

def collect_disk(path: str = "/") -> dict:
    d = psutil.disk_usage(path)
    return {"path": path, "total_bytes": d.total, "used_bytes": d.used, "free_bytes": d.free, "used_percent": d.percent}
