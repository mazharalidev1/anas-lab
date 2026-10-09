import time
from collections.abc import Callable

def run_periodically(task: Callable[[], None], interval_seconds: int) -> None:
    if interval_seconds < 1: raise ValueError("interval_seconds must be >= 1")
    while True:
        task()
        time.sleep(interval_seconds)
