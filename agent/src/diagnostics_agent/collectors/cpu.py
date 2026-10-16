import os

import psutil


def collect_cpu() -> dict:
    return {"percent": psutil.cpu_percent(interval=0.2), "logical_count": psutil.cpu_count(logical=True) or 1, "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None}
